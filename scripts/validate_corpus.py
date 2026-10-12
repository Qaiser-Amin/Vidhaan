"""Validate the real eight-domain corpus without a model or a legal-quality claim."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.document_corpus import GUIDES
from vidhaan.config import ROOT, get_settings
from vidhaan.registry import Registry
from vidhaan.answering import ResearchService
from vidhaan.models import Filters, GeneratedAnswer, utc_now
from vidhaan.citations import validate_citations
from vidhaan.official_sections import load_section_records

EXPECTED = {'Labour and employment': 'plantations-1951', 'Consumer law': 'consumer-protection-2019',
            'Contracts': 'indian-contract-1872', 'Tenancy and property': 'transfer-property-1882',
            'Family law': 'hindu-succession-1956', 'Criminal and civil procedure': 'limitation-1963',
            'Corporate and tax': 'companies-2013', 'Other specialist areas': 'information-technology-2000'}


def validate(registry, settings):
    versions = registry.versions('official')
    source_rows = []
    for version in versions:
        source = version['source']; path = registry.data_dir / version['raw_path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != source.checksum:
            raise ValueError('Original/document checksum mismatch: ' + source.document_id)
        if source.authenticity_status == 'official_sections_title_checked':
            records = load_section_records(source, path)
            if not all(c.page_start is None and c.page_end is None for c in registry.chunks(version['version_id'])):
                raise ValueError('Invented PDF pagination in section collection')
        else: records = None
        source_rows.append({'document_id': source.document_id, 'sha256': source.checksum,
                            'integrity': 'passed', 'section_records': len(records) if records else None})
    service = ResearchService(registry, settings); rows = []
    for domain, (_, _, _, _, question) in GUIDES.items():
        filters = Filters(domain=domain, jurisdiction='central', review_mode='demo')
        answer = service.answer(question, filters)
        validate_citations(GeneratedAnswer(status=answer.status, claims=answer.claims), answer.evidence)
        if answer.status != 'supported' or not any(x.source.document_id == EXPECTED[domain.value] for x in answer.evidence):
            raise ValueError('Representative domain evidence missing: ' + domain.value)
        if not all(x.source.domain == domain and x.source.namespace == 'official' for x in answer.evidence):
            raise ValueError('Domain or namespace leak')
        # These are snapshot checks, not general guarantees about future reviewed/date metadata.
        if service.answer(question, filters.model_copy(update={'review_mode': 'reviewed'})).evidence:
            raise ValueError('Unexpected reviewed evidence in this unreviewed sample')
        dated = Filters(domain=domain, jurisdiction='central', as_of='2026-10-12')
        if service.answer(question, dated).evidence: raise ValueError('Unknown-date version entered dated research')
        rows.append({'domain': domain.value, 'question': question, 'status': answer.status,
                     'expected_source_retrieved': True, 'exact_citations': 'passed',
                     'reviewed_gap': 'passed', 'unknown_date_gap': 'passed',
                     'document_ids': list(dict.fromkeys(x.source.document_id for x in answer.evidence)),
                     'evidence_ids': [x.chunk.chunk_id for x in answer.evidence],
                     'retrieval_seconds': answer.timings.get('retrieval_seconds')})
        print(domain.value + ': passed', flush=True)
    return {'created_at': utc_now(), 'corpus_signature': registry.signature('official'),
            'official_child_chunks': sum(len(registry.chunks(v['version_id'])) for v in versions),
            'sources': len(versions), 'domain_count': len(rows), 'source_integrity': source_rows, 'rows': rows,
            'scope': 'Real BM25 exact-extract workflow; no generated legal claims; human legal review pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluations/corpus_expansion_smoke.json')
    args = parser.parse_args()
    settings = get_settings()
    if args.data_dir: settings = settings.model_copy(update={'data_dir': args.data_dir.resolve()}).initialize()
    report = validate(Registry(settings.data_dir), settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
