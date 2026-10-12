"""Generate source-linked guides and an inventory from the actual official registry.

No private namespace, legal full text or API snapshots are exported by this script.
"""
import json
from pathlib import Path
from pypdf import PdfReader
from vidhaan.config import ROOT, get_settings
from vidhaan.models import Domain, utc_now
from vidhaan.registry import Registry
from vidhaan.official_sections import load_section_records

GUIDES = {
    Domain.employment: ('01_labour_employment', 'Plantation welfare, bonded labour, apprenticeships, compensation, provident funds, ESI, factories, industrial disputes, maternity, gratuity, bonus and contract-labour administration.',
        'Establishment type, employment category, location, relevant dates and contract facts.',
        'The full four Labour Codes and state employment laws are not supplied. Historical Acts and FAQ explanations do not establish current applicability.',
        'What passage covers wholesome drinking water in plantations?'),
    Domain.consumer: ('02_consumer', 'Consumer protection, legal metrology, essential commodities, mediation, e-commerce, direct selling, council/commission procedure and dark-pattern Guidelines.',
        'Transaction and complaint dates, goods or services, parties, location, value and alleged defect or deficiency.',
        'Current pecuniary-jurisdiction notifications, all later amendments (including catalogue-listed 2026 e-commerce changes), and consumer decisions are not comprehensively collected.',
        'Find the Consumer Protection Act passage on findings of the District Commission.'),
    Domain.contracts: ('03_contracts', 'Agreements, remedies, sale of goods, arbitration, partnerships, negotiable instruments, stamp duties, MSME, securities contracts and security enforcement.',
        'Complete agreement, parties and capacity, governing law, performance dates, alleged breach and remedy sought.',
        'These collections do not supply a complete case-law interpretation, sector-specific contracts or later applicable amendments.',
        'Find compensation for loss or damage caused by breach of contract.'),
    Domain.property: ('04_tenancy_property', 'Property transfers and leases, RERA, easements, trusts, partition, Benami property, registration, land acquisition and charitable trusts/endowments.',
        'State or union territory, property use, tenancy type, agreement, rent, transaction dates and any notices.',
        'State rent-control, tenancy, land-revenue and local real-estate rules are not collected. Central lease passages alone cannot decide a state eviction question.',
        'Find the Transfer of Property Act definition of a lease.'),
    Domain.family: ('05_family', 'Hindu marriage, succession, adoption/maintenance and minority/guardianship, plus Special Marriage; selected related family-property, trust, partition, BNSS maintenance and historical marital-evidence passages.',
        'Applicable personal-law framework, relationships, domicile, dates, family/property facts and relevant proceedings.',
        'Muslim, Christian and other personal-law frameworks, Family Courts Act and complete family-court procedure are absent. Related marital evidence includes the historical Evidence Act, whose transition/applicability is unreviewed.',
        'Find the Hindu Succession Act passage on devolution of interest in coparcenary property.'),
    Domain.procedure: ('06_criminal_civil_procedure', 'BNS, BNSS, BSA, historical Evidence Act, limitation, General Clauses, prevention of corruption, advocates, securities Special Court, debt recovery and economic-offence limitation.',
        'Nature of matter, court, location, offence/cause-of-action dates, procedural stage and relevant orders.',
        'The complete Code of Civil Procedure, court rules and current transition/commencement notifications are not supplied. The three criminal Acts are Gazette snapshots, not certified current consolidations.',
        'Find the Limitation Act passage about extension of the prescribed period in certain cases.'),
    Domain.corporate: ('07_corporate_tax', 'Companies, LLPs, Income Tax Act 2025, FEMA, SEBI, depositories, competition, accountancy/company-secretary professions, Black Money, multi-state cooperatives and official tax-transition FAQ.',
        'Entity type, incorporation details, transaction date, tax/assessment year, residence, relevant returns and notices.',
        'The FAQ is department guidance. GST, the historical Income-tax Act 1961, complete current tax rates, rules and all amendments are not supplied. The 2025 Act collection does not establish commencement or applicability.',
        'Find the Companies Act passage on incorporation of a company.'),
    Domain.specialist: ('08_specialist', 'IT, RTI, environmental protection, Air, Water, NGT, digital personal data protection, Aadhaar, copyright, patents, designs and trade marks.',
        'Specific issue and sector, location, dates, records, authority and applicable proceedings.',
        'Complete implementing rules, amendments, sector-regulatory notifications and case law are absent. These Act collections are unreviewed snapshots.',
        'Find legal recognition of electronic records in the Information Technology Act.'),
}


def main():
    registry = Registry(get_settings().data_dir)
    versions = registry.versions('official')
    inventory = []
    excluded = {'labour-faq-2025-12', 'labour-faq-2026-03'}
    for version in versions:
        source = version['source']; raw = registry.data_dir / version['raw_path']
        sections = load_section_records(source, raw) if source.authenticity_status == 'official_sections_title_checked' else None
        pages = len(PdfReader(raw).pages) if raw.suffix.lower() == '.pdf' else None
        inventory.append(source.model_dump(mode='json') | {
            'raw_path': version['raw_path'], 'active': bool(version['active']), 'indexed': bool(version['indexed']),
            'physical_pdf_pages': pages, 'section_records': len(sections) if sections else None,
            'child_chunks': len(registry.chunks(version['version_id'])), 'bundled': source.document_id not in excluded})
    bundled = [v for v in inventory if v['bundled']]
    data = {'created_at': utc_now(), 'corpus_signature': registry.signature('official'), 'coverage': registry.coverage('official'),
            'versions': inventory, 'official_child_chunks': sum(v['child_chunks'] for v in inventory),
            'bundle_source_count': len(bundled), 'original_api_snapshots_bundled': False,
            'reason': 'Statutory texts accompany original guides under scoped reproduction records; the tax FAQ has department reuse terms. Two Labour FAQs remain download-only.'}
    (ROOT / 'data/registry/source_inventory.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    folder = ROOT / 'docs/domains'; folder.mkdir(parents=True, exist_ok=True)
    index = ['# Domain document collection', '',
             f'{len(bundled)} distinct official-host documents and eight portable BM25 inverted indexes are included for offline loading. Each domain contains 10–15 distinct documents. Shared documents are stored once; only explicitly selected passages enter related-domain searches.', '',
             'Family law has five primary Acts and five related maintenance, property and marital-evidence sources. This is not coverage of ten different personal-law frameworks. Every source remains unreviewed; effective dates and current applicability are unknown.', '',
             '| Domain guide | Primary documents | Related documents | Total | Index |', '|---|---:|---:|---:|---|']
    details = ['# Actual source inventory', '',
               f'Collected on 12 October 2026 from government HTTPS sources: Income Tax Department, India Code, Ministry of Home Affairs, Ministry of Labour and Ministry of Consumer Affairs. {len(inventory)} retained cloud documents; {len(bundled)} distributed documents. The two Labour FAQs remain download-only.', '',
               'Full extractable Acts, Rules, Regulations, Guidelines and one department tax FAQ are counted as documents. Separate sections of an Act are not counted as separate sources. An Act may cover more than one domain, with explicit related-passage selections; domain totals therefore overlap. Source bodies, Act membership, full pagination and original SHA-256 values were checked. These checks do not establish legal currency.', '',
               '| Domain | Primary | Related | Offline total |', '|---|---:|---:|---:|']
    for domain, (slug, themes, facts, gaps, question) in GUIDES.items():
        selected = [v for v in bundled if v['domain'] == domain.value or v['related_domain_passages'].get(domain.value)]
        primary = sum(v['domain'] == domain.value for v in selected); related = len(selected)-primary
        index.append(f'| [{domain.value}]({slug}.md) | {primary} | {related} | {len(selected)} | `bm25-{domain.name}.json` |')
        details.append(f'| {domain.value} | {primary} | {related} | {len(selected)} |')
        lines = [f'# {domain.value}', '', 'Original source-linked research guide. Author: Qaiser Amin Ganaie.', '',
                 f'Collected scope: {themes}', '', f'Facts needed: {facts}', '', f'Coverage gaps: {gaps}', '',
                 f'{primary} primary documents and {related} related documents are included. Related scope is an editorial passage selection, not legal review. Shared documents are stored once.', '',
                 '| Official document | Format / extent | Domain scope | Review |', '|---|---|---|---|']
        for v in selected:
            extent = f'{v["section_records"]} section/schedule records' if v['section_records'] else f'{v["physical_pdf_pages"]} physical PDF pages'
            scope = 'Primary' if v['domain'] == domain.value else 'Selected related passages'
            lines.append(f'| [{v["title"]}]({v["official_url"]}) | {extent} | {scope} | {v["review_status"]} |')
        lines += ['', '## Example search', '', '```bash',
                  '.venv/bin/python -m vidhaan.cli search ' + repr(question) + ' --domain ' + repr(domain.value) + (' --jurisdiction central' if domain == Domain.property else ''),
                  '```', '', 'Windows uses `.venv\\Scripts\\python.exe`. Reviewed/date-scoped research returns a gap while review and effective dates remain unknown.', '', '## Provenance and related passages', '']
        for v in selected:
            lines += [f'### {v["title"]}', '', f'- Document: `{v["document_id"]}`; version: `{v["source_version"]}`.',
                      f'- SHA-256: `{v["checksum"]}`.', f'- Retrieved UTC: {v["retrieved_at"]}.',
                      f'- Publication date: {v["publication_date"] or "unknown"}; effective date: {v["effective_date"] or "unknown"}.',
                      f'- Provenance: {v["provenance_notes"] or "Government-host source; currency unreviewed"}', '']
            for selector in v['related_domain_passages'].get(domain.value, []): lines.append('- Related selection: `' + selector + '`.')
            lines.append('')
        lines += ['PDF citations retain physical pages; unknown printed pages stay unknown. Department collections retain exact section/schedule labels and per-section source links. Compact receipts reproduce document bytes and retain acquisition response hashes. Original API payloads are excluded.', '',
                  'Offline index: `data/bundled/indexes/bm25-' + domain.name + '.json`. It contains lexical postings, lengths, source checksums and chunk fingerprints. Loading verifies it against local source chunks before reuse. Source exclusions and related-passage scope changes rebuild the affected index. Review/date/jurisdiction eligibility is applied before BM25 scoring.', '',
                  'See [source inventory](../../DATA_SOURCES.md), [reuse records](../CORPUS_REUSE.md) and [domain index](README.md).', '']
        (folder / (slug + '.md')).write_text('\n'.join(lines), encoding='utf-8')
    (folder / 'README.md').write_text('\n'.join(index) + '\n', encoding='utf-8')
    details += ['', '## Source versions', '']
    for v in inventory:
        details += [f'### {v["title"]}', '', f'- Primary domain: {v["domain"]}; document: `{v["document_id"]}`.',
                    f'- Official source: {v["official_url"]}', f'- Retrieved UTC: {v["retrieved_at"]}.',
                    f'- SHA-256: `{v["checksum"]}`; child passages: {v["child_chunks"]}.',
                    f'- Extent: {v["physical_pdf_pages"] or "no PDF pages"}; section/schedule records: {v["section_records"] or "not applicable"}.',
                    f'- Distributed: {v["bundled"]}; review: {v["review_status"]}; publication: {v["publication_date"] or "unknown"}; effective date: {v["effective_date"] or "unknown"}.',
                    f'- Related domains: {", ".join(v["related_domain_passages"]) or "none"}.',
                    f'- Provenance: {v["provenance_notes"] or "Government-host source; legal currency unreviewed"}', '']
    details += ['## Integrity, exclusions and reuse', '',
                'The acquisition manifest records body-title checks, exact official URLs, bounded full pagination and inspected SHA-256 values. Section text retains footnotes and schedules; no fabricated PDF pagination or missing-section substitute is introduced. Brackets denoting editorial interpolation and curly apostrophes are normalized only for title identity checks, never in retained source bodies.', '',
                'India Code backend discovery returned no usable family results. Several government links returned HTTP 403/timeouts, regional translations or scanned text. The CrPC API collection contained an unrenderable section and was rejected rather than imported partially. Failed sources do not count. See `data/registry/acquisition_domain_expansion.json` for outcomes.', '',
                'Acts accompany original guides under the scoped Copyright Act section 52(1)(q)(ii) basis. Consumer Gazette Rules/Regulations/Guidelines retain individual Gazette references under section 52(1)(q)(i). The tax FAQ uses department reuse terms. Source/Taxmann notices remain intact; no blanket publisher licence is asserted. Raw API payloads, private data, databases, models and runtime indexes are excluded. Only verified official-domain portable indexes are distributed. See [CORPUS_REUSE.md](docs/CORPUS_REUSE.md).', '',
                'All versions remain unreviewed. Historical Acts are retained as research sources without claiming that they are current. State/UT laws, many personal-law frameworks, full CPC, complete notifications and case law remain gaps. Dense/hybrid model indexes are optional and were not built for this release.', '']
    (ROOT / 'DATA_SOURCES.md').write_text('\n'.join(details), encoding='utf-8')
    print(json.dumps({'cloud_sources': len(inventory), 'bundled_sources': len(bundled), 'cloud_child_passages': data['official_child_chunks'], 'domain_guides': len(GUIDES)}))


if __name__ == '__main__': main()
