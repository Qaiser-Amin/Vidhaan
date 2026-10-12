"""Synthetic read-only API fixtures, never genuine legal evidence."""
import json
import httpx
import pytest
from vidhaan.official_sections import html_body_text, load_section_records, section_chunks
from vidhaan.sources import download_manifest


def item(identity, number, body, category=42):
    return {'itemURL': 'https://www.incometaxindia.gov.in/o/headless-delivery/v1.0/structured-contents/' + str(identity),
            'embedded': {'id': identity, 'friendlyUrlPath': 'synthetic-' + str(identity),
                         'taxonomyCategoryBriefs': [{'taxonomyCategoryId': category}],
                         'contentFields': [
                             {'name': 'sectionNumber', 'contentFieldValue': {'data': number}},
                             {'name': 'sectionShortDescription', 'contentFieldValue': {'data': 'SYNTHETIC label'}},
                             {'name': 'documentContent', 'contentFieldValue': {'data': '<body><p>' + body + '</p></body>'}}]}}


def acquisition(registry, tmp_path, scenario='success'):
    entry = {'adapter': 'incometax_sections', 'category_id': 42,
             'url': 'https://www.incometaxindia.gov.in/synthetic-test', 'filename': 'synthetic.txt',
             'title_check': 'SYNTHETIC ACT, 2026',
             'metadata': {'document_id': 'synthetic-api', 'title': 'SYNTHETIC ACT, 2026',
                          'domain': 'Contracts', 'instrument_type': 'Act', 'namespace': 'synthetic'}}
    if scenario == 'checksum': entry['expected_sha256'] = '0' * 64
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'allowed_hosts': ['www.incometaxindia.gov.in'], 'sources': [entry]}))
    def handler(request):
        assert request.method == 'POST'
        assert json.loads(request.content)['attributes']['search.experiences.act_id'] == 42
        page = int(request.url.params['page'])
        if scenario == 'redirect': return httpx.Response(307, headers={'location': 'https://evil.example/api'})
        body = 'SYNTHETIC ACT, 2026. A duty applies unless an express exception is satisfied.'
        if scenario == 'title': body = 'A different synthetic instrument without the expected title.'
        record = item(1 if page == 1 or scenario == 'duplicate' else 2,
                      '1' if page == 1 else 'Schedule', body, 99 if scenario == 'scope' else 42)
        if scenario == 'missing_body': record['embedded']['contentFields'][-1]['contentFieldValue']['data'] = ''
        return httpx.Response(200, json={'page': page, 'pageSize': 1, 'lastPage': 2, 'totalCount': 3 if scenario == 'incomplete' else 2,
                                         'items': [record]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return download_manifest(registry, manifest, client)


def test_html_keeps_qualifiers_inline_words_tables_and_footnotes():
    html = '<html><head><title>IGNORE</title></head><body><style>IGNORE</style><script>IGNORE</script><p>Duty <b>shall</b> apply unless exempt.</p><table><tr><td>First</td><td>Second</td></tr></table><div>Footnote: subject to review.</div></body></html>'
    text = html_body_text(html)
    assert 'Duty shall apply unless exempt.' in text
    assert 'First Second' in text and 'Footnote: subject to review.' in text
    assert 'IGNORE' not in text


@pytest.mark.parametrize('scenario', ['redirect', 'title', 'scope', 'duplicate', 'missing_body', 'incomplete', 'checksum'])
def test_refuses_partial_wrong_scope_wrong_title_or_altered_collections(registry, tmp_path, scenario):
    result = acquisition(registry, tmp_path, scenario)
    assert result[0]['status'] == 'failed'
    assert not registry.versions()


def test_complete_import_retains_raw_snapshots_exact_locators_and_idempotence(registry, tmp_path):
    result = acquisition(registry, tmp_path)
    assert result[0]['status'] == 'imported' and result[0]['section_records'] == 2
    version = registry.versions()[0]
    source = version['source']
    assert source.review_status == 'unreviewed' and source.effective_date is None
    raw_path = registry.data_dir / version['raw_path']
    records = load_section_records(source, raw_path)
    assert len(records) == 2
    children = registry.chunks(version['version_id'])
    assert {c.locator for c in children} == {'Section 1: SYNTHETIC label', 'Schedule: SYNTHETIC label'}
    assert all(c.page_start is None and c.page_end is None for c in children)
    assert all(c.text.strip() in raw_path.read_text() for c in children)
    assert [c.chunk_id for c in section_chunks(source, records) if c.kind == 'child'] == [c.chunk_id for c in children]
    assert acquisition(registry, tmp_path)[0]['status'] == 'duplicate'
    assert len(registry.versions()) == 1
    from vidhaan.cli import main
    signature = registry.signature('synthetic')
    assert main(['--data-dir', str(registry.data_dir), 'rechunk']) == 0
    assert registry.signature('synthetic') == signature


@pytest.mark.parametrize('target', ['document', 'receipt', 'response'])
def test_rechunk_checks_original_and_derived_integrity(registry, tmp_path, target):
    acquisition(registry, tmp_path)
    version = registry.versions()[0]
    raw_path = registry.data_dir / version['raw_path']
    receipt_path = raw_path.parent / 'section_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    if target == 'document': raw_path.write_text('changed')
    elif target == 'receipt':
        receipt['sections'][0]['body'] = 'changed'; receipt_path.write_text(json.dumps(receipt))
    else: (raw_path.parent / receipt['responses'][0]['filename']).write_text('changed')
    with pytest.raises(ValueError): load_section_records(version['source'], raw_path)
