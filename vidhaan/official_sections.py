"""Read the Income Tax Department's public English Act collection.

The site's own Act viewer uses this search API. Preserve the original JSON,
render body text without executing HTML, and retain authoritative section labels.
This is a department compilation, not a certification of current law.
"""
from html.parser import HTMLParser
import hashlib
import json
import re
from .chunking import stable_id, split_exact
from .models import Chunk

ORIGIN = 'https://www.incometaxindia.gov.in'
API = ORIGIN + '/o/search/v1.0/search'
RENDERER = 'official-sections-v1'


class BodyText(HTMLParser):
    """Keep visible words, qualifiers, tables and footnotes; ignore executable data."""
    blocks = {'p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'table', 'ul', 'ol'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'body': self.in_body = True
        if tag in {'script', 'style', 'head'}: self.skip += 1
        if self.in_body and not self.skip:
            if tag in self.blocks or tag == 'br': self.parts.append('\n')
            elif tag in {'td', 'th'}: self.parts.append('\t')

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'head'} and self.skip: self.skip -= 1
        if self.in_body and not self.skip and tag in self.blocks: self.parts.append('\n')
        if tag == 'body': self.in_body = False

    def handle_data(self, data):
        if self.in_body and not self.skip: self.parts.append(data)

    def text(self):
        # HTML layout whitespace is normalized; legal wording is not rewritten.
        lines = [' '.join(line.split()) for line in ''.join(self.parts).splitlines()]
        return '\n'.join(line for line in lines if line).strip()


def html_body_text(html):
    parser = BodyText()
    # Some department fields contain fragments instead of full HTML documents.
    parser.feed(html if re.search(r'<body\b', html, re.I) else '<body>' + html + '</body>')
    return parser.text()


def render_items(items, category_id):
    records = []
    seen = set()
    for item in items:
        embedded = item['embedded']
        identity = str(embedded['id'])
        if identity in seen: raise ValueError('Duplicate section ID in official collection')
        seen.add(identity)
        categories = {int(c['taxonomyCategoryId']) for c in embedded.get('taxonomyCategoryBriefs', [])}
        if int(category_id) not in categories:
            raise ValueError('Official section belongs to a different Act')
        fields = {f['name']: f.get('contentFieldValue', {}) for f in embedded['contentFields']}
        number = str(fields.get('sectionNumber', {}).get('data', '')).strip()
        description = str(fields.get('sectionShortDescription', {}).get('data', '')).strip()
        body = html_body_text(fields.get('documentContent', {}).get('data', ''))
        if not number or len(body) < 10:
            raise ValueError('Collection contains an unrenderable section; refusing a partial import')
        footnotes = html_body_text(fields.get('footnotes', {}).get('data', ''))
        if footnotes and footnotes not in body:
            body += '\nDepartment footnotes (separate source field):\n' + footnotes
        locator = ('Section ' + number if re.fullmatch(r'\d+[A-Za-z]*', number) else number)
        if description: locator += ': ' + description
        records.append({'id': identity, 'number': number, 'locator': locator,
                        'source_url': ORIGIN + '/w/' + embedded['friendlyUrlPath'],
                        'api_url': item['itemURL'], 'body': body})
    # Do not depend on the search index's occasional ordering of section 2 before 1.
    def order(record):
        match = re.fullmatch(r'(\d+)([A-Za-z]*)', record['number'])
        return (0, int(match[1]), match[2]) if match else (1, 0, record['number'])
    return sorted(records, key=order)


def document_bytes(entry, records):
    header = (entry['metadata']['title'] + '\n\n'
              'Source: Income Tax Department, Ministry of Finance, Government of India\n'
              + entry['url'] + '\n'
              'English department collection; legal currency and applicability unreviewed.\n'
              'Editorial section labels precede source body text. HTML layout whitespace is normalized.\n'
              'No physical PDF pagination is asserted. Original API responses and section links are retained.\n\n')
    return (header + '\n\n'.join('[' + r['locator'] + ']\n' + r['body'] for r in records) + '\n').encode('utf-8')


def section_chunks(source, records):
    chunks = []
    ordinal = 0
    for record in records:
        text = '[' + record['locator'] + ']\n' + record['body'] + '\n'
        parent_id = stable_id(source.source_version, RENDERER, record['id'], text)
        jurisdiction = 'unknown' if re.search(r'STATE\s+AMENDMENT', text, re.I) else source.jurisdiction
        common = dict(version_id=source.source_version, source_checksum=source.checksum,
                      document_id=source.document_id, domain=source.domain, namespace=source.namespace,
                      jurisdiction=jurisdiction, locator=record['locator'], page_start=None, page_end=None)
        chunks.append(Chunk(**common, chunk_id=parent_id, ordinal=ordinal, kind='parent', text=text))
        for start, end, piece in split_exact(text):
            chunks.append(Chunk(**common, chunk_id=stable_id(parent_id, start, piece),
                                ordinal=ordinal, kind='child', parent_id=parent_id, text=piece))
            ordinal += 1
    return chunks


def fetch_sections(client, entry, allowlist, request_bytes):
    if not entry['url'].startswith(ORIGIN + '/') or not isinstance(entry.get('category_id'), int):
        raise ValueError('Unsupported official collection origin or category ID')
    category_id = entry['category_id']
    payload = {'attributes': {'search.empty.search': True,
               'search.experiences.blueprint.external.reference.code': 'ACT_SECTIONS_BP_ERC',
               'search.experiences.act_id': category_id}}
    responses, items, total, last_page, size = [], [], None, None, 0
    page = 1
    while True:
        url = API + f'?nestedFields=embedded&page={page}&pageSize=200&restrictFields=embedded.actions,embedded.creator'
        raw, final_url = request_bytes(client, url, allowlist, method='POST', payload=payload)
        size += len(raw)
        if size > 25 * 1024 * 1024: raise ValueError('Official collection exceeds 25 MiB')
        data = json.loads(raw)
        count, last = data['totalCount'], data['lastPage']
        if not isinstance(count, int) or not 1 <= count <= 1500 or not isinstance(last, int) or not 1 <= last <= 10:
            raise ValueError('Unexpected official collection count or pagination')
        if total is not None and (count != total or last != last_page):
            raise ValueError('Collection changed during acquisition; retry as a new snapshot')
        total, last_page = count, last
        if data['page'] != page or not data['items']:
            raise ValueError('Missing official response page')
        items.extend(data['items'])
        responses.append({'url': final_url, 'request': payload,
                          'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': raw})
        if page == last_page: break
        page += 1
    if len(items) != total: raise ValueError('Incomplete official collection')
    records = render_items(items, category_id)
    # Check the title against actual source body text, never our editorial title.
    actual = ' '.join(' '.join(r['body'] for r in records).split()).casefold()
    if entry['title_check'].casefold() not in actual:
        raise ValueError('Official body does not contain the expected Act title')
    return document_bytes(entry, records), records, responses


def load_section_records(source, raw_path):
    """Rebuild from checksum-verified original responses, not editable derived labels."""
    from pathlib import Path
    raw_path = Path(raw_path)
    if hashlib.sha256(raw_path.read_bytes()).hexdigest() != source.checksum:
        raise ValueError('Section document checksum mismatch')
    receipt = json.loads((raw_path.parent / 'section_receipt.json').read_text(encoding='utf-8'))
    if receipt['renderer'] != RENDERER: raise ValueError('Unsupported section renderer')
    if receipt.get('receipt_mode') == 'bundled-section-records-v1':
        expected = re.search(r'bundle_receipt_sha256=([0-9a-f]{64})', source.provenance_notes or '')
        if not expected or hashlib.sha256((raw_path.parent / 'section_receipt.json').read_bytes()).hexdigest() != expected[1]:
            raise ValueError('Bundled section receipt checksum mismatch')
        records = receipt['sections']
        if not isinstance(records, list) or not 1 <= len(records) <= 1500:
            raise ValueError('Invalid bundled section count')
        if len({r['id'] for r in records}) != len(records): raise ValueError('Duplicate bundled section ID')
        if receipt['source_document_sha256'] != source.checksum: raise ValueError('Bundled receipt belongs to a different document')
        rendered = document_bytes({'metadata': {'title': source.title}, 'url': source.official_url}, records)
        if hashlib.sha256(rendered).hexdigest() != source.checksum:
            raise ValueError('Bundled section records do not reproduce the source document')
        return records
    if receipt.get('receipt_mode') is not None: raise ValueError('Unsupported section receipt mode')
    items = []
    expected_total = None
    for response in receipt['responses']:
        name = response['filename']
        if name != 'response-' + response['sha256'] + '.json': raise ValueError('Invalid snapshot filename')
        raw = (raw_path.parent / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != response['sha256']: raise ValueError('Response checksum mismatch')
        data = json.loads(raw)
        if expected_total is not None and expected_total != data['totalCount']:
            raise ValueError('Inconsistent original response counts')
        expected_total = data['totalCount']
        items.extend(data['items'])
    if len(items) != expected_total: raise ValueError('Incomplete response snapshots')
    records = render_items(items, receipt['category_id'])
    if records != receipt['sections']: raise ValueError('Derived section receipt differs from original responses')
    rendered = document_bytes({'metadata': {'title': source.title}, 'url': source.official_url}, records)
    if hashlib.sha256(rendered).hexdigest() != source.checksum:
        raise ValueError('Original responses do not reproduce the indexed document')
    return records
