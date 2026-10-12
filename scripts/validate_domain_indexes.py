"""Validate the distributed official corpus and portable indexes in a fresh registry."""
import json
from pathlib import Path
import tempfile
import httpx
from vidhaan.bundled import verify_bundle, load_bundle
from vidhaan.config import ROOT, get_settings
from vidhaan.lexical import build_all, snapshot
from vidhaan.models import Domain, Filters, utc_now
from vidhaan.registry import Registry
from vidhaan.retrieval import Retriever
from scripts.validate_corpus import validate


def main():
    manifest, paths = verify_bundle(ROOT/'data/bundled')
    # Loading, indexing and extractive validation must succeed with network disabled.
    original_client = httpx.Client
    httpx.Client = lambda *a, **k: (_ for _ in ()).throw(AssertionError('Offline validation cannot use the network'))
    try:
        with tempfile.TemporaryDirectory(prefix='vidhaan-domain-validation-') as temporary:
            settings = get_settings().model_copy(update={'data_dir': Path(temporary), 'profile': 'evidence_only'}).initialize()
            registry = Registry(settings.data_dir); results = load_bundle(registry, ROOT/'data/bundled')
            assert all(row['status'] == 'imported' for row in results)
            coverage = registry.coverage('official')
            assert all(10 <= row['sources'] <= 15 for row in coverage)
            indexes = build_all(registry)
            versions = registry.versions('official'); chunks = registry.chunks(namespace='official')
            for entry, report in zip(manifest['indexes'], indexes):
                assert entry['domain'] == report['domain'] and entry['signature'] == report['signature']
                assert entry['source_count'] == report['sources'] and entry['chunk_count'] == report['chunks']
                actual = json.loads((settings.data_dir/'indexes'/report['file']).read_text())
                rows, *_ = snapshot(Domain(report['domain']), versions, chunks)
                assert actual['chunk_ids'] == [c.chunk_id for c in rows]
            family = Retriever(registry, settings).search('maintenance wives children parents sufficient means neglects refuses', Filters(domain=Domain.family, jurisdiction='central'))
            assert any(hit.source.document_id == 'bnss-2023' for hit in family)
            assert all(hit.source.includes_passage(hit.chunk, Domain.family) for hit in family)
            corpus = validate(registry, settings)
            report = {'created_at': utc_now(), 'status': 'passed', 'network': 'disabled',
                      'unique_sources': len(versions), 'source_integrity': corpus['source_integrity'],
                      'section_collections': sum(bool(e.get('section_receipt')) for e in manifest['sources']),
                      'official_child_passages': corpus['official_child_chunks'], 'corpus_signature': corpus['corpus_signature'],
                      'coverage': coverage, 'indexes': indexes, 'representative_searches': corpus['rows'],
                      'family_related_maintenance': 'passed', 'dense_indexes': 'not built; optional weights unavailable',
                      'legal_review': 'pending'}
            (ROOT/'evaluations/domain_index_validation.json').write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps({k: report[k] for k in ['status', 'unique_sources', 'official_child_passages', 'section_collections']}, indent=2))
    finally:
        httpx.Client = original_client


if __name__ == '__main__': main()
