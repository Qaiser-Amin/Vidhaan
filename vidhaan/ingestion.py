from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import io
import re
from pypdf import PdfReader
from .chunking import Page, chunk_pages, stable_id
from .models import Source, utc_now
from .registry import Registry


@dataclass
class IngestionResult:
    version_id: str
    created: bool
    chunks: int
    warnings: list[str] = field(default_factory=list)


def safe_filename(name: str) -> str:
    name = Path(name.replace('\\', '/')).name
    clean = re.sub(r'[^A-Za-z0-9_. -]', '_', name).strip(' .')
    if not clean or clean in ('.', '..'):
        raise ValueError("A valid filename is required")
    return clean[:140]


def extract(content: bytes, suffix: str) -> tuple[list[Page], list[str]]:
    warnings = []
    if suffix == '.pdf':
        if not content.startswith(b'%PDF-'):
            raise ValueError("Content is not a PDF, regardless of filename")
        try:
            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs require an unlocked local copy")
            if len(reader.pages) > 1500:
                raise ValueError("PDF page limit exceeded (1500)")
            pages = []
            total_characters = 0
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ''
                total_characters += len(text)
                if total_characters > 10_000_000:
                    raise ValueError('Extracted text exceeds the bounded processing limit')
                if not text.strip():
                    warnings.append(f"Physical PDF page {number}: empty extraction; OCR may be needed")
                pages.append(Page(number, text))
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Cannot parse PDF: {type(exc).__name__}") from exc
    elif suffix in ('.txt', '.md'):
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must be UTF-8") from exc
        if '\x00' in text:
            raise ValueError("Binary content is not a text document")
        pages = [Page(None, text)]
    else:
        raise ValueError("Supported formats: PDF, TXT and Markdown")
    if sum(len(p.text.strip()) for p in pages) < 20:
        warnings.append("No usable text: scanned/image-only or empty document; needs OCR")
    if sum(len(p.text) for p in pages) > 10_000_000:
        raise ValueError("Extracted text exceeds the bounded processing limit")
    return pages, warnings


def ingest_bytes(registry: Registry, content: bytes, filename: str, source: Source,
                 max_bytes=25 * 1024 * 1024) -> IngestionResult:
    if not content or len(content) > max_bytes:
        raise ValueError("File is empty or exceeds 25 MiB upload limit")
    filename = safe_filename(filename)
    suffix = Path(filename).suffix.lower()
    pages, warnings = extract(content, suffix)
    checksum = hashlib.sha256(content).hexdigest()
    duplicate = registry.duplicate(source.namespace, checksum)
    if duplicate:
        return IngestionResult(duplicate['version_id'], False, len(registry.chunks(duplicate['version_id'])), warnings)
    # Caller cannot turn an unchecked import into a reviewed version.
    source = Source.model_validate(dict(source.model_dump(), checksum=checksum,
        source_version=stable_id(source.namespace, source.document_id, checksum),
        retrieved_at=source.retrieved_at or utc_now(), review_status='unreviewed', last_verification_date=None,
        reviewer_notes=None, extraction_warnings=warnings,
        parsing_status='parsed' if any(p.text.strip() for p in pages) else 'needs_ocr'))
    usable = sum(len(p.text.strip()) for p in pages) >= 20
    if not usable:
        source.parsing_status = 'needs_ocr'
    chunks = chunk_pages(pages, source) if usable else []
    folder = registry.data_dir / ('private' if source.namespace.startswith('private:') else 'raw') / source.source_version
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
        raise ValueError("Refusing to overwrite an existing original file")
    path.write_bytes(content)
    version, created = registry.add(source, path, chunks)
    return IngestionResult(version, created, len([c for c in chunks if c.kind == 'child']), warnings)


def ingest_file(registry: Registry, path: Path, source: Source) -> IngestionResult:
    path = Path(path)
    if path.stat().st_size > 25 * 1024 * 1024:
        raise ValueError("File exceeds the configured limit")
    return ingest_bytes(registry, path.read_bytes(), path.name, source)
