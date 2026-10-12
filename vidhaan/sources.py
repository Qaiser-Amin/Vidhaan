"""Explicit HTTPS manifest acquisition. No commercial scraping or automatic crawling."""
from pathlib import Path
from urllib.parse import urlsplit, urljoin
import json
import ssl
import os
import hashlib
import httpx
from .models import Source, utc_now
from .ingestion import extract, ingest_bytes, safe_filename


def request_bytes(client, url, allowlist, method='GET', payload=None):
    """Bounded requests; validate every destination and preserve TLS verification."""
    for _ in range(5):
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.hostname not in allowlist or parts.username or parts.password or parts.port not in (None,443):
            raise ValueError('Destination is outside the explicit HTTPS host allowlist')
        headers = {'User-Agent': 'VIDHAAN-University-Research/0.1', 'Accept-Language': 'en-US'}
        with client.stream(method, url, headers=headers, json=payload) as response:
            if response.is_redirect:
                if method != 'GET' and response.status_code not in (307, 308):
                    raise ValueError('Unexpected redirect for official read-only search')
                url = urljoin(url, response.headers['location'])
                continue
            response.raise_for_status()
            if int(response.headers.get('content-length', '0')) > 25 * 1024 * 1024:
                raise ValueError('Remote file exceeds 25 MiB')
            buffer = bytearray()
            for block in response.iter_bytes(65536):
                buffer.extend(block)
                if len(buffer) > 25 * 1024 * 1024: raise ValueError('Download exceeds 25 MiB')
            return bytes(buffer), url
    raise ValueError('Redirect limit exceeded')


def download_manifest(registry, manifest: Path, client=None):
    config = json.loads(Path(manifest).read_text(encoding='utf-8'))
    allowlist = set(config['allowed_hosts'])
    own_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(30, connect=10), follow_redirects=False,
        verify=ssl.create_default_context(cafile=os.getenv('SSL_CERT_FILE') or None))
    log = []
    try:
        for entry in config['sources']:
            record = {'document_id': entry['metadata']['document_id'], 'attempted_at': utc_now(),
                      'url': entry['url'], 'status': 'failed'}
            try:
                records, responses = None, []
                if entry.get('adapter') == 'incometax_sections':
                    from .official_sections import fetch_sections
                    content, records, responses = fetch_sections(client, entry, allowlist, request_bytes)
                    url = entry['url']
                elif entry.get('adapter') is None:
                    content, url = request_bytes(client, entry['url'], allowlist)
                else:
                    raise ValueError('Unknown acquisition adapter')
                if entry.get('expected_sha256') and hashlib.sha256(content).hexdigest()!=entry['expected_sha256']:
                    raise ValueError('Official file differs from the recorded sample checksum; inspect it as a new source version')
                filename = safe_filename(entry.get('filename') or Path(urlsplit(url).path).name)
                pages, warnings = extract(content, Path(filename).suffix.lower())
                actual = ' '.join(p.text for p in pages[:5]).casefold()
                expected = entry.get('title_check')
                if not expected or records is None and expected.casefold() not in ' '.join(actual.split()):
                    raise ValueError("Downloaded text does not contain the manifest's expected title")
                notes = entry['metadata'].get('provenance_notes') or ''
                source = Source(**dict(entry['metadata'], official_url=url, retrieved_at=utc_now(),
                                      authenticity_status='official_sections_title_checked' if records else 'official_host_title_checked',
                                      provenance_notes=(notes + '\nHTTPS host and source body title checked; legal currency unverified').strip()))
                result = ingest_bytes(registry, content, filename, source)
                if records:
                    from .official_sections import section_chunks, RENDERER
                    if result.created:
                        registry.replace_chunks(result.version_id, section_chunks(registry.source(result.version_id), records))
                    folder = registry.data_dir / 'raw' / result.version_id
                    receipt = {'renderer': RENDERER, 'category_id': entry['category_id'], 'sections': records, 'responses': []}
                    for number, response in enumerate(responses, 1):
                        snapshot = 'response-' + response['sha256'] + '.json'
                        (folder / snapshot).write_bytes(response['bytes'])
                        receipt['responses'].append({k:v for k,v in response.items() if k != 'bytes'} | {'filename': snapshot})
                    (folder / 'section_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
                record.update(status='imported' if result.created else 'duplicate', final_url=url,
                              version_id=result.version_id, checksum=registry.source(result.version_id).checksum,
                              title_check=expected, warnings=result.warnings)
                if records: record.update(section_records=len(records), response_checksums=[r['sha256'] for r in responses])
            except Exception as exc:
                record['error'] = f'{type(exc).__name__}: {str(exc)[:400]}'
            log.append(record)
    finally:
        if own_client:
            client.close()
    path = registry.data_dir / 'registry' / 'acquisition.jsonl'
    with path.open('a', encoding='utf-8') as output:
        for record in log:
            output.write(json.dumps(record) + '\n')
    return log
