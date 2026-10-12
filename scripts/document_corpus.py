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
    Domain.employment: ('01_labour_employment', 'Plantation welfare, bonded labour, contract-labour administration and department explanations of Labour Codes.',
        'Establishment type, employment category, location, relevant dates and contract facts.',
        'The full four Labour Codes and state employment laws are not supplied. Historical Acts and FAQ explanations do not establish current applicability.',
        'What passage covers wholesome drinking water in plantations?'),
    Domain.consumer: ('02_consumer', 'Consumer definitions, complaints, consumer commissions, remedies, mediation and product liability in the department-hosted 2019 Act collection.',
        'Transaction and complaint dates, goods or services, parties, location, value and alleged defect or deficiency.',
        'Rules, current pecuniary-jurisdiction notifications, later amendments and consumer decisions are not comprehensively collected.',
        'Find the Consumer Protection Act passage on findings of the District Commission.'),
    Domain.contracts: ('03_contracts', 'Agreements, consent, breach, specific performance, injunctions and sale-of-goods conditions in three Act collections.',
        'Complete agreement, parties and capacity, governing law, performance dates, alleged breach and remedy sought.',
        'These collections do not supply a complete case-law interpretation, sector-specific contracts or later applicable amendments.',
        'Find compensation for loss or damage caused by breach of contract.'),
    Domain.property: ('04_tenancy_property', 'Central property-transfer and lease provisions, plus real-estate regulation and promoter/allottee provisions.',
        'State or union territory, property use, tenancy type, agreement, rent, transaction dates and any notices.',
        'State rent-control, tenancy, land-revenue and local real-estate rules are not collected. Central lease passages alone cannot decide a state eviction question.',
        'Find the Transfer of Property Act definition of a lease.'),
    Domain.family: ('05_family', 'Hindu marriage and Hindu succession collections, including marriage conditions, divorce and inheritance passages.',
        'Applicable personal-law framework, relationships, domicile, dates, family/property facts and relevant proceedings.',
        'Special Marriage, Muslim, Christian and other personal laws, adoption/guardianship laws and family-court procedure are not comprehensively supplied.',
        'Find the Hindu Succession Act passage on devolution of interest in coparcenary property.'),
    Domain.procedure: ('06_criminal_civil_procedure', 'English Gazette texts of BNS, BNSS and BSA, plus the Limitation Act collection for suits, appeals and applications.',
        'Nature of matter, court, location, offence/cause-of-action dates, procedural stage and relevant orders.',
        'The complete Code of Civil Procedure, court rules and current transition/commencement notifications are not supplied. The three criminal Acts are Gazette snapshots, not certified current consolidations.',
        'Find the Limitation Act passage about extension of the prescribed period in certain cases.'),
    Domain.corporate: ('07_corporate_tax', 'Companies and limited-liability-partnership Act collections, plus official Income-tax Act transition FAQs.',
        'Entity type, incorporation details, transaction date, tax/assessment year, residence, relevant returns and notices.',
        'The FAQ is department guidance, not the full Income-tax Act. GST, complete current tax rates, corporate rules and all amendments are not supplied.',
        'Find the Companies Act passage on incorporation of a company.'),
    Domain.specialist: ('08_specialist', 'Information Technology, Environment Protection and Right to Information Act collections.',
        'Specific issue and sector, location, dates, records, authority and applicable proceedings.',
        'Specialist coverage is a sample: complete data-protection, intellectual-property, sector-regulatory and environmental notification/case-law collections are absent.',
        'Find legal recognition of electronic records in the Information Technology Act.'),
}


def main():
    registry = Registry(get_settings().data_dir)
    versions = registry.versions('official')
    coverage = registry.coverage('official')
    inventory = []
    for version in versions:
        source = version['source']
        raw = registry.data_dir / version['raw_path']
        sections = load_section_records(source, raw) if source.authenticity_status == 'official_sections_title_checked' else None
        pages = len(PdfReader(raw).pages) if raw.suffix.lower() == '.pdf' else None
        inventory.append(source.model_dump(mode='json') | {
            'raw_path': version['raw_path'], 'active': bool(version['active']), 'indexed': bool(version['indexed']),
            'physical_pdf_pages': pages, 'section_records': len(sections) if sections else None,
            'child_chunks': len(registry.chunks(version['version_id']))})
    data = {'created_at': utc_now(), 'corpus_signature': registry.signature('official'), 'coverage': coverage,
            'versions': inventory, 'official_child_chunks': sum(v['child_chunks'] for v in inventory),
            'raw_files_bundled': (ROOT/'data/bundled/manifest.json').exists(),
            'bundle_source_count': len(json.loads((ROOT/'data/bundled/manifest.json').read_text())['sources']) if (ROOT/'data/bundled/manifest.json').exists() else 0,
            'original_api_snapshots_bundled': False,
            'reason': 'Selected statutory texts accompany original guides under the recorded reproduction basis. The tax FAQ has department reuse terms; two Labour FAQs require permission and stay download-only. Original API payloads are not bundled.'}
    (ROOT / 'data/registry/source_inventory.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    folder = ROOT / 'docs/domains'; folder.mkdir(parents=True, exist_ok=True)
    index = ['# Domain document collection', '',
             'Source-linked research guides for all eight VIDHAAN domains. These guides describe the collected material; they do not reproduce restricted legal compilations or establish current law.', '',
             f'Actual cloud collection: {len(inventory)} sources/versions; {data["official_child_chunks"]} child passages; zero legally reviewed versions. The final project includes 21 selected source documents across all eight domains for offline loading; two Labour FAQs remain optional downloads.', '',
             '| Domain guide | Indexed sources |', '|---|---:|']
    details = ['# Actual source inventory', '',
               'Collected from official Ministry of Labour, Ministry of Home Affairs and Income Tax Department websites on 12 October 2026. HTTPS hosts and actual source body titles were checked. Fetching/indexing confers no legal review.', '',
               '| Domain | Sources | Indexed | Reviewed |', '|---|---:|---:|---:|']
    for row in coverage:
        domain = Domain(row['domain']); slug, themes, facts, gaps, question = GUIDES[domain]
        selected = [v for v in inventory if v['domain'] == domain.value]
        index.append(f'| [{domain.value}]({slug}.md) | {row["indexed"]} |')
        details.append(f'| {domain.value} | {row["sources"]} | {row["indexed"]} | {row["reviewed"]} |')
        lines = [f'# {domain.value}', '', 'VIDHAAN source-linked research guide. Author: Qaiser Amin Ganaie.', '',
                 f'Collected scope: {themes}', '', f'Facts needed for case-specific research: {facts}', '',
                 f'Coverage gaps: {gaps}', '',
                 '| Collected document | Format and extent | Review |', '|---|---|---|']
        for v in selected:
            extent = f'English section collection; {v["section_records"]} records' if v['section_records'] else f'PDF; {v["physical_pdf_pages"]} physical pages'
            lines.append(f'| [{v["title"]}]({v["official_url"]}) | {extent} | {v["review_status"]} |')
        lines += ['', '## Example local search', '', '```bash',
                  '.venv/bin/python -m vidhaan.cli search ' + repr(question) + ' --domain ' + repr(domain.value) + (' --jurisdiction central' if domain == Domain.property else ''),
                  '```', '', 'Windows uses `.venv\\Scripts\\python.exe`. Effective-date filters exclude unknown versions. Reviewed research currently returns a gap.', '',
                  '## Provenance', '']
        for v in selected:
            lines += [f'### {v["title"]}', '',
                      f'- Document: `{v["document_id"]}`; version: `{v["source_version"]}`.',
                      f'- Source document SHA-256: `{v["checksum"]}`.',
                      f'- Retrieved (UTC): {v["retrieved_at"]}.',
                      f'- Local document: `data/{v["raw_path"]}`; {v["child_chunks"]} indexed child passages.',
                      f'- Publication date: {v["publication_date"] or "unknown"}; effective date: {v["effective_date"] or "unknown"}.',
                      f'- Provenance: {v["provenance_notes"] or "Official source; legal currency unreviewed"}', '']
        lines += ['PDF citations use physical pages; section collections use department section/schedule labels and retain acquisition response hashes and per-section links. The bundle has checksum-verified compact records; original API payloads stay in the acquisition workspace. The plain-text document is a reproducible rendering, not an original Gazette PDF.', '',
                  'The final project includes selected full source documents and these original guides. Two Labour FAQs remain download-only. Private data, databases, models and original API payloads are excluded. See [DATA_SOURCES.md](../../DATA_SOURCES.md), [reuse records](../CORPUS_REUSE.md) and the [collection index](README.md).', '']
        (folder / (slug + '.md')).write_text('\n'.join(lines), encoding='utf-8')
    (folder / 'README.md').write_text('\n'.join(index) + '\n', encoding='utf-8')
    details += ['', '## Source versions', '']
    for v in inventory:
        details += [f'### {v["title"]}', '',
                    f'- Domain: {v["domain"]}; document: `{v["document_id"]}`; version: `{v["source_version"]}`.',
                    f'- Official source: {v["official_url"]}', f'- Retrieved (UTC): {v["retrieved_at"]}.',
                    f'- SHA-256: `{v["checksum"]}`; child passages: {v["child_chunks"]}.',
                    f'- Physical PDF pages: {v["physical_pdf_pages"] or "not applicable"}; API section/schedule records: {v["section_records"] or "not applicable"}.',
                    f'- Review: {v["review_status"]}; publication date: {v["publication_date"] or "unknown"}; effective date: {v["effective_date"] or "unknown"}.',
                    f'- Provenance: {v["provenance_notes"] or "Official file; legal currency unreviewed"}', '']
    details += ['## Acquisition, integrity and reuse', '',
                'The manifest records exact official URLs, English body-title checks and inspected source-document SHA-256 values. PDF downloads retain original bytes and physical pagination. The Income Tax Department Act viewer uses the public read-only search API: the adapter collects every returned page, checks Act membership, rejects missing/duplicate sections, retains raw JSON hashes, and renders English body text without executing scripts. Title checks inspect source body text rather than an inserted editorial header. Schedules and authoritative section labels are retained; no PDF page numbers are fabricated.', '',
                'Thirteen Act documents are section collections. Network acquisition retains original responses; the project bundle includes verified compact section records, acquisition response hashes and exact source links. Compact receipt checksums are recorded in source provenance. Rechunking validates those records against source bytes and preserves authoritative locators. Original HTML/API payloads are not redistributed. The collection is not a current or exhaustive legal consolidation.', '',
                'The final project includes 21 selected sources (19 Acts, one Rules compilation and one official tax FAQ) with original domain guides and reproduction/attribution records. Statutory texts accompany original matter under Copyright Act section 52(1)(q); the tax FAQ uses the department reuse policy. Taxmann notices remain intact; no blanket publisher/database licence is asserted. Two Labour Ministry FAQs require reproduction permission and remain download-only. See [CORPUS_REUSE.md](docs/CORPUS_REUSE.md). Run `python -m vidhaan.cli load-bundled` for offline loading; `acquire` remains an explicit online refresh/optional-download command.', '',
                'The initial five employment files remain intact. Their repeated acquisition previously returned four verified duplicates and a Bonded Labour HTTP 403; the acquired original remains usable offline. The expansion acquisition imported all 18 new sources successfully. A later byte change triggers a checksum error requiring a deliberate inspected version update, not a silent replacement.', '',
                'India Code public backend searches returned zero records during this expansion. Several government/judicial hosts returned proxy denials. Legislative Department alternatives inspected were scanned or regional-language translations and were excluded from the searchable English collection. Failed discovery is not indexed coverage; see `acquisition_discovery.json`.', '',
                'The inspected cloud collection has 23 versions and 5,819 official child passages; the offline bundle has 21 versions and 5,786 passages. All effective dates remain unknown and every version is unreviewed. State/UT rent and employment laws, other personal-law frameworks, the full CPC, full tax statutes, complete notifications and case law remain gaps. Mixed state-amendment passages are conservatively scoped unknown. The eight-domain guide index is [docs/domains/README.md](docs/domains/README.md).', '']
    (ROOT / 'DATA_SOURCES.md').write_text('\n'.join(details), encoding='utf-8')
    print(json.dumps({'sources': len(inventory), 'child_passages': data['official_child_chunks'], 'domain_guides': len(GUIDES)}))


if __name__ == '__main__': main()
