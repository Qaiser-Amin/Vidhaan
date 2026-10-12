"""Checksum-verified, explicit offline import of the project's selected public corpus."""
from pathlib import Path
import hashlib
import json
import re
import shutil
from .models import Source

BASES = {'legislation_with_original_matter', 'official_gazette_matter', 'department_reuse_policy'}


def checked_path(folder, relative):
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('Invalid bundle path')
    name = Path(relative)
    if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] not in {'documents', 'sections', 'guides'}:
        raise ValueError('Bundle path is outside the selected corpus directories')
    path = folder / name
    if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
        raise ValueError('Bundle symlink or escaped path')
    if not path.is_file() or path.stat().st_size > 25 * 1024 * 1024:
        raise ValueError('Bundle file missing or exceeds 25 MiB')
    if path.suffix.lower() not in {'.pdf', '.txt', '.json', '.md'}:
        raise ValueError('Unsupported bundle file format')
    return path


def verify_bundle(folder):
    """Verify the complete allowlist and reuse records before importing any source."""
    folder = Path(folder).resolve()
    manifest_path = folder / 'manifest.json'
    if manifest_path.is_symlink(): raise ValueError('Bundle manifest cannot be a symlink')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or manifest.get('generated_by') != 'VIDHAAN selected corpus':
        raise ValueError('Unsupported corpus bundle')
    files = manifest['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= 100:
        raise ValueError('Invalid bundle file count')
    paths = {}
    for relative, checksum in files.items():
        if not isinstance(checksum, str) or not re.fullmatch(r'[0-9a-f]{64}', checksum):
            raise ValueError('Invalid bundle checksum')
        path = checked_path(folder, relative)
        if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError('Bundle checksum mismatch: ' + relative)
        paths[relative] = path
    entries = manifest['sources']
    if not isinstance(entries, list) or not 1 <= len(entries) <= 50:
        raise ValueError('Invalid bundled source count')
    seen = set()
    for entry in entries:
        source = Source(**entry['source'])
        if source.namespace != 'official' or source.review_status != 'unreviewed' or source.last_verification_date is not None:
            raise ValueError('Bundle must contain unreviewed official research sources only')
        from .chunking import stable_id
        if source.supersedes or source.source_version != stable_id('official', source.document_id, source.checksum):
            raise ValueError('Invalid bundled source version identity')
        if source.document_id in seen: raise ValueError('Duplicate bundled document')
        seen.add(source.document_id)
        if entry.get('reuse_basis') not in BASES or not entry.get('reuse_reference'):
            raise ValueError('Missing scoped source reuse basis')
        if entry.get('guide') not in paths or not entry['guide'].startswith('guides/'):
            raise ValueError('Original accompanying domain guide is required')
        if entry.get('file') not in paths or not entry['file'].startswith('documents/'):
            raise ValueError('Undeclared bundled source file')
        if paths[entry['file']].suffix.lower() not in {'.pdf', '.txt', '.md'}:
            raise ValueError('Unsupported bundled document format')
        if files[entry['file']] != source.checksum:
            raise ValueError('Source metadata differs from bundle file checksum')
        if entry['reuse_basis'] == 'legislation_with_original_matter' and source.instrument_type != 'Act':
            raise ValueError('Legislative reuse basis does not match the instrument')
        if source.authenticity_status == 'official_sections_title_checked':
            receipt_name = entry.get('section_receipt')
            if receipt_name not in paths or not receipt_name.startswith('sections/'):
                raise ValueError('Verified section receipt required')
            expected = re.search(r'bundle_receipt_sha256=([0-9a-f]{64})', source.provenance_notes or '')
            if not expected or files[receipt_name] != expected[1]: raise ValueError('Section receipt differs from source provenance')
            receipt = json.loads(paths[receipt_name].read_text(encoding='utf-8'))
            from .official_sections import document_bytes, RENDERER
            if receipt.get('receipt_mode') != 'bundled-section-records-v1' or receipt.get('renderer') != RENDERER:
                raise ValueError('Unsupported bundled section receipt')
            if receipt['source_document_sha256'] != source.checksum:
                raise ValueError('Section receipt belongs to a different document')
            records = receipt['sections']
            if not 1 <= len(records) <= 1500 or len({r['id'] for r in records}) != len(records):
                raise ValueError('Invalid bundled section records')
            reproduced = document_bytes({'metadata': {'title': source.title}, 'url': source.official_url}, records)
            if hashlib.sha256(reproduced).hexdigest() != source.checksum:
                raise ValueError('Bundled section records do not reproduce source bytes')
    return manifest, paths


def load_bundle(registry, folder):
    """Import locally; preserve reviewed, excluded and user-updated versions on repeats."""
    from .ingestion import ingest_file
    from .official_sections import load_section_records, section_chunks
    manifest, paths = verify_bundle(folder)
    existing = registry.versions('official')
    results = []
    for entry in manifest['sources']:
        source = Source(**entry['source'])
        versions = [v for v in existing if v['document_id'] == source.document_id]
        same = next((v for v in versions if v['checksum'] == source.checksum), None)
        if same:
            results.append({'document_id': source.document_id, 'status': 'existing', 'version_id': same['version_id']})
            continue
        if versions:
            results.append({'document_id': source.document_id, 'status': 'skipped_existing_version'})
            continue
        result = ingest_file(registry, paths[entry['file']], source)
        if entry.get('section_receipt') and result.created:
            stored = registry.source(result.version_id)
            target = registry.data_dir / 'raw' / result.version_id
            shutil.copy2(paths[entry['section_receipt']], target / 'section_receipt.json')
            original = target / paths[entry['file']].name
            records = load_section_records(stored, original)
            registry.replace_chunks(result.version_id, section_chunks(stored, records))
        results.append({'document_id': source.document_id, 'status': 'imported' if result.created else 'existing',
                        'version_id': result.version_id, 'child_chunks': len(registry.chunks(result.version_id))})
    return results
