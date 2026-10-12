"""Prepare only selected official sources with scoped reuse records; never export private data."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from vidhaan.config import ROOT, get_settings
from vidhaan.registry import Registry
from vidhaan.official_sections import load_section_records, RENDERER
from vidhaan.bundled import verify_bundle, load_bundle
from vidhaan.lexical import payload, filename
from scripts.document_corpus import GUIDES

COPYRIGHT = 'https://www.incometaxindia.gov.in/w/section-52-114'
EXCLUDED = {'labour-faq-2025-12', 'labour-faq-2026-03'}


def prepare():
    registry = Registry(get_settings().data_dir)
    acquisition = json.loads((ROOT / 'data/registry/source_manifest.json').read_text())
    selected = {x['metadata']['document_id'] for x in acquisition['sources']} - EXCLUDED
    acquisition_by_id = {x['metadata']['document_id']: x for x in acquisition['sources']}
    versions = [v for v in registry.versions('official') if v['document_id'] in selected and v['active']]
    if len(versions) != len(selected): raise ValueError('Acquire one active inspected version of each selected source first')
    staging = Path(tempfile.mkdtemp(prefix='.bundle-stage-', dir=ROOT / 'data'))
    manifest = {'schema_version': 1, 'generated_by': 'VIDHAAN selected corpus', 'files': {}, 'sources': [],
                'notes': 'Original statutory texts accompany original domain guides. This is not a blanket licence to publisher commentary or a certification of current law.',
                'download_only': [{'document_id': x, 'reason': 'Ministry copyright policy requires reproduction permission; omitted from distributed corpus',
                                   'policy': 'https://www.labour.gov.in/policies/copyright-policy'} for x in sorted(EXCLUDED)]}
    def write(name, content):
        target = staging / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
        manifest['files'][name] = hashlib.sha256(content).hexdigest()
    try:
        for domain, (slug, *_rest) in GUIDES.items():
            guide=(ROOT / 'docs/domains' / (slug + '.md')).read_text(encoding='utf-8')
            guide=guide.replace('../../DATA_SOURCES.md','../../../DATA_SOURCES.md').replace('../CORPUS_REUSE.md','../../../docs/CORPUS_REUSE.md')
            write('guides/' + slug + '.md', guide.encode())
        write('guides/README.md',(ROOT/'docs/domains/README.md').read_bytes())
        for version in versions:
            source = version['source']; original = registry.data_dir / version['raw_path']
            content = original.read_bytes()
            if hashlib.sha256(content).hexdigest() != source.checksum: raise ValueError('Acquired original checksum mismatch')
            name = 'documents/' + source.document_id + original.suffix.lower(); write(name, content)
            entry = {'file': name, 'guide': 'guides/' + GUIDES[source.domain][0] + '.md'}
            if source.instrument_type == 'Act':
                entry.update(reuse_basis='legislation_with_original_matter', reuse_reference=COPYRIGHT + ' — Copyright Act, 1957, section 52(1)(q)(ii)')
            elif source.instrument_type in {'Rules', 'Regulations', 'Guidelines'}:
                inspected = acquisition_by_id[source.document_id]
                reference = inspected.get('reuse_reference')
                if not reference and source.document_id == 'contract-labour-rules-1971':
                    reference = COPYRIGHT + ' — section 52(1)(q)(i); G.S.R. 190/191 reproduced in source'
                if not reference: raise ValueError('Inspected Gazette reuse reference required: ' + source.document_id)
                entry.update(reuse_basis='official_gazette_matter', reuse_reference=reference)
            elif source.document_id == 'income-tax-transition-faq-2026' and source.redistribution_permitted:
                entry.update(reuse_basis='department_reuse_policy', reuse_reference='https://www.incometaxindia.gov.in/copyright-policy')
            else: raise ValueError('No established bundle reuse basis: ' + source.document_id)
            notes = (source.provenance_notes or '') + '\nIncluded in the VIDHAAN educational project with original domain guide and source acknowledgment; scoped reuse basis recorded in the bundle manifest.'
            if source.authenticity_status == 'official_sections_title_checked':
                records = load_section_records(source, original)
                old = json.loads((original.parent / 'section_receipt.json').read_text())
                receipt = {'renderer': RENDERER, 'receipt_mode': 'bundled-section-records-v1', 'category_id': old['category_id'],
                           'source_document_sha256': source.checksum, 'sections': records,
                           'acquisition_response_checksums': [r['sha256'] for r in old['responses']],
                           'note': 'Verified body records and acquisition hashes; original HTML/API payloads retained in the acquisition workspace, not redistributed.'}
                receipt_name = 'sections/' + source.document_id + '.json'
                write(receipt_name, (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())
                notes += '\nbundle_receipt_sha256=' + manifest['files'][receipt_name]
                entry['section_receipt'] = receipt_name
            entry['source'] = source.model_copy(update={'provenance_notes': notes}).model_dump(mode='json')
            manifest['sources'].append(entry)
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        # Build against precisely the offline document/receipt rendering, never the
        # cloud database (which can contain extra sources or private sessions).
        from vidhaan.models import Domain
        with tempfile.TemporaryDirectory(prefix='vidhaan-official-index-') as temporary:
            offline = Registry(Path(temporary))
            load_bundle(offline, staging)
            offline_versions = offline.versions('official'); chunks = offline.chunks(namespace='official')
            manifest['indexes'] = []
            for domain in Domain:
                index = payload(domain, offline_versions, chunks)
                if not 10 <= len(index['sources']) <= 15:
                    raise ValueError('The release requires 10–15 sources per domain: ' + domain.value)
                name = 'indexes/' + filename(domain)
                write(name, (json.dumps(index, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
                manifest['indexes'].append({'domain': domain.value, 'file': name, 'source_count': len(index['sources']),
                                            'chunk_count': len(index['chunk_ids']), 'signature': index['signature']})
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        verify_bundle(staging)
        target = ROOT / 'data/bundled'
        if target.exists():
            prior = json.loads((target / 'manifest.json').read_text())
            if prior.get('generated_by') != manifest['generated_by']: raise ValueError('Refusing to replace an unknown collection')
            backup = ROOT / 'data/.bundle-previous'
            if backup.exists(): raise ValueError('Previous bundle backup requires inspection')
            target.rename(backup)
            try: staging.rename(target)
            except Exception: backup.rename(target); raise
            shutil.rmtree(backup)
        else: staging.rename(target)
        return {'sources': len(versions), 'domains': len(GUIDES), 'files': len(manifest['files']), 'download_only': sorted(EXCLUDED)}
    finally:
        if staging.exists(): shutil.rmtree(staging)


if __name__ == '__main__': print(json.dumps(prepare(), indent=2))
