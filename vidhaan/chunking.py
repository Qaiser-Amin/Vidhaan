"""Exact-text section parents plus bounded children; no embedding truncation."""
from dataclasses import dataclass
import hashlib
import re
from .models import Chunk, Source

CHUNKER_VERSION = "sections-v3"
SECTION = re.compile(r"(?m)^\s*(?:Section\s+)?(\d+[A-Z]?)\.[ \t]+([^\n]{3,120})")


@dataclass
class Page:
    number: int | None
    text: str


def stable_id(*parts):
    return hashlib.sha256("\0".join(map(str, parts)).encode()).hexdigest()[:24]


def split_exact(text: str, limit=1100, tokenizer=None):
    """Split on paragraph/line/word boundaries, without dropping even a qualifier.

    With a tokenizer, count special tokens too; split a single long word safely.
    The concatenation of outputs equals the original text.
    """
    def size(s):
        return len(tokenizer.encode(s, add_special_tokens=True, truncation=False)) if tokenizer else len(s)
    offset = 0
    while offset < len(text):
        low, high = 1, len(text) - offset
        while low < high:
            mid = (low + high + 1) // 2
            if size(text[offset:offset + mid]) <= limit:
                low = mid
            else:
                high = mid - 1
        end = offset + low
        if size(text[offset:end]) > limit:
            raise ValueError("Token budget cannot fit even a single character with special tokens")
        if end < len(text):
            window = text[offset:end]
            boundary = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(" "))
            if boundary > len(window) // 2:
                end = offset + boundary + 1
        piece = text[offset:end]
        yield offset, end, piece
        offset = end


def chunk_pages(pages: list[Page], source: Source, tokenizer=None, limit=None) -> list[Chunk]:
    text = ""
    spans = []
    for page in pages:
        start = len(text)
        text += page.text + "\n"
        spans.append((start, len(text), page.number))
    matches = list(SECTION.finditer(text))
    body_start = 0
    if 'ARRANGEMENT OF SECTIONS' in text.upper():
        enactment = re.search(r'BE\s+it\s+enacted', text, re.I)
        if enactment:
            body_start = enactment.start()
    starts = [(0, None)]
    for match in matches:
        heading = match.group(2).strip()
        # Editorial footnotes are retained inside surrounding parents, never called sections.
        if re.match(r'(?:Subs\.|Ins\.|Omitted|Added|See |Vide |The Act comes into|\d+(?:st|nd|rd|th)\s)', heading, re.I):
            continue
        prefix = 'Section' if source.instrument_type == 'Act' and re.search(r'[. ](?:—|–|-)\s*', heading) else 'Numbered paragraph'
        if match.start() > starts[-1][0]:
            starts.append((match.start(), f"{prefix} {match.group(1)}: {match.group(2).strip()}"))
        elif match.start() == 0:
            starts[0] = (0, f"{prefix} {match.group(1)}: {match.group(2).strip()}")
    chunks = []
    ordinal = 0
    def make(start, end, content, kind, parent_id, locator, identity):
        numbers = [n for a, b, n in spans if a < end and b > start and n is not None]
        return Chunk(chunk_id=identity, version_id=source.source_version, source_checksum=source.checksum,
                     document_id=source.document_id, domain=source.domain, jurisdiction=source.jurisdiction,
                     namespace=source.namespace, ordinal=ordinal, kind=kind, parent_id=parent_id,
                     page_start=min(numbers) if numbers else None, page_end=max(numbers) if numbers else None,
                     locator=locator, content_role='contents' if body_start and end<=body_start else 'text', text=content)
    for i, (start, locator) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        section = text[start:end]
        if not section.strip():
            continue
        parent_id = stable_id(source.source_version, CHUNKER_VERSION, "parent", i, section)
        mixed = bool(re.search(r'STATE\s+AMENDMENT', section, re.I))
        parent = make(start, end, section, "parent", None, locator, parent_id)
        if mixed:
            parent.jurisdiction = 'unknown'  # Never silently treat a state amendment as a central rule.
        chunks.append(parent)
        for child_start, child_end, part in split_exact(section, limit or (384 if tokenizer else 1100), tokenizer):
            child_id = stable_id(parent_id, child_start, part)
            child = make(start + child_start, start + child_end, part, "child", parent_id, locator, child_id)
            if mixed:
                child.jurisdiction = 'unknown'
            chunks.append(child)
            ordinal += 1
    return chunks
