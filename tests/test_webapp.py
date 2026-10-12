"""Real local API tests: source workflow, exports, isolation and browser boundaries."""
from fastapi.testclient import TestClient
import pytest
from vidhaan.config import Settings
from vidhaan.webapp import create_app


@pytest.fixture
def workspace(tmp_path):
    app = create_app(Settings(data_dir=tmp_path).initialize())
    with TestClient(app) as client:
        csrf = client.get('/api/bootstrap').json()['csrf']
        client.headers['X-Vidhaan-CSRF'] = csrf
        yield app, client


def test_custom_interface_and_fixture_research(workspace):
    app, client = workspace
    page = client.get('/')
    assert page.status_code == 200 and '<div id="root">' in page.text
    assert "script-src 'self'" in page.headers['content-security-policy']
    assert client.get('/api/health').json()['assets_ready']
    assert client.post('/api/corpus/synthetic').status_code == 200
    result = client.post('/api/research', json={'question': 'written consent', 'corpus': 'synthetic'}).json()
    assert result['status'] == 'supported' and 'SYNTHETIC' in result['text']
    assert result['evidence'] and result['evidence'][0]['reference']
    assert not client.post('/api/research', json={'question': 'written consent'}).json()['evidence']


def test_original_context_and_session_exports(workspace):
    app, client = workspace
    client.post('/api/corpus/synthetic')
    answer = client.post('/api/research', json={'question': 'written consent', 'corpus': 'synthetic'}).json()
    chunk = answer['evidence'][0]['chunk']
    assert client.get('/api/chunks/' + chunk['chunk_id']).json()['parent']['text']
    version = client.get('/api/sources/' + chunk['version_id']).json()
    assert version['child_count'] > 0 and version['parent_count'] > 0
    assert client.get(f"/api/sources/{chunk['version_id']}/download").status_code == 200
    assert client.get(f"/api/sources/{chunk['version_id']}/passages?limit=1").json()['items']
    export = client.get(f"/api/exports/{answer['answer_id']}?format=markdown")
    assert export.status_code == 200 and '# VIDHAAN research record' in export.text
    assert export.headers['cache-control'] == 'no-store'
    assert client.get(f"/api/exports/{answer['answer_id']}?format=json").json()['status'] == 'supported'
    client.post(f"/api/sources/{chunk['version_id']}/exclude")
    assert client.get(f"/api/exports/{answer['answer_id']}").status_code == 404


def test_private_isolation_and_clear(workspace):
    app, first = workspace
    imported = first.post('/api/private/upload', files={'file': ('clause.txt', b'The tenant shall give written consent before assignment.')}, data={'domain': 'Contracts'})
    assert imported.status_code == 200, imported.text
    version_id = imported.json()['version_id']
    assert len(first.get('/api/sources?scope=private').json()) == 1
    answer = first.post('/api/research', json={'question': 'written consent', 'corpus': 'private'}).json()
    assert answer['status'] == 'supported' and answer['mode'] == 'private extracts'
    with TestClient(app) as second:
        second.headers['X-Vidhaan-CSRF'] = second.get('/api/bootstrap').json()['csrf']
        assert not second.get('/api/sources?scope=private').json()
        assert second.get(f'/api/sources/{version_id}').status_code == 404
        assert second.get(f'/api/sources/{version_id}/download').status_code == 404
        assert second.get('/api/chunks/' + answer['evidence'][0]['chunk']['chunk_id']).status_code == 404
        assert second.get('/api/exports/' + answer['answer_id']).status_code == 404
        assert second.post('/api/research', json={'question': 'consent', 'version_ids': [version_id]}).status_code == 400
        second.post('/api/private/clear')
        assert len(first.get('/api/sources?scope=private').json()) == 1
    first.post('/api/private/clear')
    assert not first.get('/api/sources?scope=private').json()
    assert not list(app.state.registry.data_dir.glob('private/**/*.*'))


def test_cross_origin_and_csrf(workspace):
    app, client = workspace
    assert client.post('/api/corpus/synthetic', headers={'Origin': 'https://example.invalid'}).status_code == 403
    assert client.post('/api/corpus/synthetic', headers={'X-Vidhaan-CSRF': 'invalid'}).status_code == 403
    assert client.get('/api/bootstrap', headers={'Host': 'rebind.invalid'}).status_code == 400
    with TestClient(app) as fresh:
        assert fresh.get('/api/sources').status_code == 401
        assert fresh.post('/api/research', json={'question': 'consent'}).status_code == 403


def test_input_bounds_and_source_modes(workspace):
    app, client = workspace
    assert client.post('/api/research', json={'question': 'a' * 2001}).status_code == 422
    assert client.post('/api/research', json={'question': 'consent', 'namespace': 'private:arbitrary'}).status_code == 422
    assert client.post('/api/research', json={'question': 'consent', 'corpus': 'private', 'retrieval': 'dense'}).status_code == 400
    assert client.post('/api/research', json={'question': 'consent', 'generate': True}).status_code == 400
    assert client.post('/api/private/upload', files={'file': ('invalid.pdf', b'not a PDF')}).status_code == 400
    assert client.post('/api/corpus/synthetic').status_code == 200
    version_id = client.get('/api/sources?scope=synthetic').json()[0]['version_id']
    assert client.post(f'/api/sources/{version_id}/review', json={'status': 'reviewed', 'notes': 'test'}).status_code == 400
    assert client.get('/api/evaluation').status_code == 200
    assert client.get('/api/diagnostics').json()['profile'] == 'evidence_only'


def test_official_manual_review_remains_audited(workspace):
    app, client = workspace
    from vidhaan.ingestion import ingest_bytes
    from vidhaan.models import Source, Domain
    source = Source(document_id='test-official', title='Test source for software validation', domain=Domain.contracts)
    imported = ingest_bytes(app.state.registry, b'Section 1. Written consent is required by this software test.', 'test.txt', source)
    version_id = imported.version_id
    assert client.post(f'/api/sources/{version_id}/review', json={'status': 'reviewed', 'notes': ' '}).status_code == 400
    result = client.post(f'/api/sources/{version_id}/review', json={'status': 'reviewed', 'notes': 'Test reviewer; software fixture only.', 'verified_on': '2026-10-12'})
    assert result.status_code == 200
    assert app.state.registry.source(version_id).effective_date is None
    with app.state.registry.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM audit WHERE action='manual_review'").fetchone()[0] == 1
    assert client.post('/api/research', json={'question': 'written consent', 'corpus': 'reviewed'}).json()['evidence']


def test_upload_file_and_streamed_envelope_limits(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path, max_file_bytes=64).initialize())) as client:
        client.headers['X-Vidhaan-CSRF'] = client.get('/api/bootstrap').json()['csrf']
        assert client.post('/api/private/upload', files={'file': ('big.txt', b'x' * 65)}).status_code == 413
        assert client.post('/api/private/upload', content=b'', headers={'Content-Length': '99999999'}).status_code == 413
        body = [b'--x\r\nContent-Disposition: form-data; name="file"; filename="big.txt"\r\n\r\n', b'x' * 66000, b'\r\n--x--\r\n']
        result = client.post('/api/private/upload', content=iter(body), headers={'Content-Type': 'multipart/form-data; boundary=x'})
        assert result.status_code == 413, result.text
        assert not client.get('/api/sources?scope=private').json()
