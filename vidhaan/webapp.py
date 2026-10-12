"""Same-origin, local single-user API and self-contained web interface.

Each opaque browser session owns its private namespace and in-memory answers.
Questions never appear in URLs, access logs, or persistent session storage.
"""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from threading import RLock
from typing import Literal
from urllib.parse import urlsplit
import hashlib
import json
import secrets
import time

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .answering import ResearchService
from .citations import export_markdown, reference
from .config import ROOT, get_settings
from .models import Domain, Filters, Source
from .registry import Registry

WEB = Path(__file__).parent / 'web'
COOKIE = 'vidhaan_session'


class BodyTooLarge(Exception):
    pass


class BodyLimit:
    """Bound streamed request bodies before multipart parsing can spool them."""
    def __init__(self, app, max_file_bytes):
        self.app = app
        self.max_file_bytes = max_file_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] in ('GET', 'HEAD'):
            return await self.app(scope, receive, send)
        limit = self.max_file_bytes + 65536 if scope['path'] == '/api/private/upload' else 32768
        headers = dict(scope['headers'])
        try:
            length = int(headers.get(b'content-length', b'0'))
        except ValueError:
            length = 0
        if length > limit:
            return await JSONResponse({'detail': 'Request exceeds the upload or input limit.'}, status_code=413)(scope, receive, send)
        consumed = 0

        async def bounded_receive():
            nonlocal consumed
            message = await receive()
            consumed += len(message.get('body', b''))
            if consumed > limit:
                raise BodyTooLarge()
            return message

        try:
            await self.app(scope, bounded_receive, send)
        except BodyTooLarge:
            await JSONResponse({'detail': 'Request exceeds the upload or input limit.'}, status_code=413)(scope, receive, send)


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=2000)
    corpus: Literal['demo', 'reviewed', 'synthetic', 'private'] = 'demo'
    domain: Domain | None = None
    jurisdiction: Literal['central', 'state'] | None = None
    state: str | None = Field(None, max_length=100)
    as_of: date | None = None
    version_ids: list[str] = Field(default_factory=list, max_length=100)
    include_superseded: bool = False
    retrieval: Literal['bm25', 'dense', 'hybrid'] = 'bm25'
    profile: Literal['evidence_only', 'lenovo_cpu', 'mac_m5'] = 'evidence_only'
    generate: bool = False
    compare_private: bool = False


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['unreviewed', 'reviewed', 'rejected']
    notes: str = Field(min_length=1, max_length=5000)
    verified_on: date | None = None


@dataclass
class Session:
    namespace: str = field(default_factory=lambda: 'private:' + secrets.token_hex(24))
    csrf: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    used: float = field(default_factory=time.monotonic)
    services: dict = field(default_factory=dict)
    answer: object = None
    answer_id: str | None = None
    signatures: dict = field(default_factory=dict)


def public_url(value):
    if not value:
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password else None


def create_app(settings=None):
    settings = settings or get_settings()
    registry = Registry(settings.data_dir)
    sessions = {}
    # Single local process; serialize retrieval/cache and corpus mutation together.
    guard = RLock()
    app = FastAPI(title='VIDHAAN local workspace', docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]', 'testserver'])
    app.state.registry = registry
    # BodyLimit goes inside exception handling to produce one bounded 413 response.
    @app.exception_handler(BodyTooLarge)
    async def oversized_body(request, exc):
        return JSONResponse({'detail': 'Request exceeds the upload or input limit.'}, status_code=413)

    app.add_middleware(BodyLimit, max_file_bytes=settings.max_file_bytes)

    def reset_answers():
        for session in sessions.values():
            session.answer = None
            session.answer_id = None
            for service in session.services.values():
                service.clear_cache()

    @app.middleware('http')
    async def boundaries(request, call_next):
        # No automatic CORS: browsers must use the same host and port.
        if request.url.path.startswith('/api/') and request.method not in ('GET', 'HEAD'):
            origin = request.headers.get('origin')
            if origin and origin != str(request.base_url).rstrip('/'):
                return JSONResponse({'detail': 'Cross-origin requests are not allowed.'}, status_code=403)
            with guard:
                session = sessions.get(request.cookies.get(COOKIE))
                token = request.headers.get('x-vidhaan-csrf', '')
                if not session or time.monotonic() - session.used > 43200 or not secrets.compare_digest(token.encode(), session.csrf.encode()):
                    return JSONResponse({'detail': 'Session expired. Reload the workspace before continuing.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(ValueError)
    async def invalid_value(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=400)

    def current(request):
        with guard:
            session = sessions.get(request.cookies.get(COOKIE))
            if not session or time.monotonic() - session.used > 43200:
                raise HTTPException(401, 'Session expired. Reload the workspace.')
            session.used = time.monotonic()
            return session

    def namespace(scope, session):
        if scope not in ('official', 'synthetic', 'private'):
            raise HTTPException(400, 'Unknown source collection.')
        return session.namespace if scope == 'private' else scope

    def version_for(version_id, session):
        # Look only in this session's permitted namespaces, never arbitrary paths.
        for name in ('official', 'synthetic', session.namespace):
            found = next((v for v in registry.versions(name) if v['version_id'] == version_id), None)
            if found:
                return found
        raise HTTPException(404, 'Source version not found.')

    def source_json(version):
        return {
            'version_id': version['version_id'], 'active': bool(version['active']),
            'indexed': bool(version['indexed']), 'source': version['source'].model_dump(mode='json'),
        }

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'interface': 'react', 'assets_ready': (WEB / 'index.html').is_file()}

    @app.get('/api/bootstrap')
    def bootstrap(request: Request, response: Response):
        with guard:
            token = request.cookies.get(COOKIE)
            session = sessions.get(token)
            if not session or time.monotonic() - session.used > 43200:
                if len(sessions) >= 128:
                    oldest = min(sessions, key=lambda key: sessions[key].used)
                    del sessions[oldest]  # Do not silently erase retained files.
                token = secrets.token_urlsafe(32)
                session = sessions[token] = Session()
                response.set_cookie(COOKIE, token, httponly=True, samesite='strict', path='/')
            session.used = time.monotonic()
            rows = registry.coverage('official')
            versions = registry.versions('official')
            active = {v['version_id'] for v in versions if v['active'] and v['indexed']}
            with registry.connection() as db:
                revision = db.execute("SELECT value FROM state WHERE key='revision'").fetchone()[0]
            return {
                'csrf': session.csrf, 'domains': [d.value for d in Domain], 'coverage': rows,
                'revision': revision, 'profile': settings.profile,
                'totals': {'sources': len({v['document_id'] for v in versions}), 'versions': len(versions),
                           'indexed': len(active), 'reviewed': sum(v['source'].review_status == 'reviewed' for v in versions),
                           'passages': sum(c.version_id in active for c in registry.chunks(namespace='official'))},
                'private_sources': len(registry.versions(session.namespace)),
                'bundle_available': (ROOT / 'data/bundled/manifest.json').exists(),
                'bundle_sources': len(json.loads((ROOT / 'data/bundled/manifest.json').read_text())['sources'])
                                  if (ROOT / 'data/bundled/manifest.json').exists() else 0,
            }

    @app.get('/api/sources')
    def sources(request: Request, scope: Literal['official', 'synthetic', 'private'] = 'official'):
        session = current(request)
        with guard:
            return [source_json(v) for v in registry.versions(namespace(scope, session))]

    @app.get('/api/sources/{version_id}')
    def source_detail(version_id: str, request: Request):
        session = current(request)
        with guard:
            version = version_for(version_id, session)
            parents = registry.chunks(version_id, 'parent')
            return {**source_json(version), 'parent_count': len(parents),
                    'child_count': len(registry.chunks(version_id)),
                    'official_link': public_url(version['source'].official_url)}

    @app.get('/api/sources/{version_id}/passages')
    def passages(version_id: str, request: Request, offset: int = Query(0, ge=0),
                 limit: int = Query(12, ge=1, le=30), query: str = Query('', max_length=200)):
        session = current(request)
        with guard:
            version_for(version_id, session)
            rows = registry.chunks(version_id, 'parent')
            if query.strip():
                rows = [c for c in rows if query.casefold() in (c.text + ' ' + (c.locator or '')).casefold()]
            return {'total': len(rows), 'items': [c.model_dump(mode='json') for c in rows[offset:offset + limit]]}

    @app.get('/api/sources/{version_id}/download')
    def download_source(version_id: str, request: Request):
        session = current(request)
        with guard:
            version = version_for(version_id, session)
            path = (registry.data_dir / version['raw_path']).resolve()
            if not path.is_relative_to(registry.data_dir.resolve()) or not path.is_file():
                raise HTTPException(404, 'Local original unavailable.')
            return FileResponse(path, filename=path.name, media_type='application/octet-stream')

    @app.get('/api/chunks/{chunk_id}')
    def chunk_context(chunk_id: str, request: Request):
        session = current(request)
        with guard:
            chunk = registry.chunk(chunk_id)
            if not chunk or chunk.namespace not in ('official', 'synthetic', session.namespace):
                raise HTTPException(404, 'Passage not found.')
            version = version_for(chunk.version_id, session)
            parent = registry.chunk(chunk.parent_id) if chunk.parent_id else chunk
            section_url = None
            if version['source'].authenticity_status == 'official_sections_title_checked':
                receipt_path = (registry.data_dir / version['raw_path']).parent / 'section_receipt.json'
                if receipt_path.is_file():
                    records = json.loads(receipt_path.read_text())['sections']
                    row = next((r for r in records if r['locator'] == chunk.locator), None)
                    section_url = public_url(row['source_url']) if row else None
            return {'chunk': chunk.model_dump(mode='json'), 'parent': parent.model_dump(mode='json') if parent else None,
                    'source': version['source'].model_dump(mode='json'), 'section_url': section_url,
                    'official_link': public_url(version['source'].official_url)}

    @app.post('/api/research')
    def research(payload: ResearchRequest, request: Request):
        session = current(request)
        with guard:
            corpus_namespace = session.namespace if payload.corpus == 'private' else 'synthetic' if payload.corpus == 'synthetic' else 'official'
            if payload.version_ids:
                permitted = {v['version_id'] for v in registry.versions(corpus_namespace)}
                if not set(payload.version_ids) <= permitted:
                    raise HTTPException(400, 'Selected versions must belong to the selected collection.')
            if payload.corpus == 'private' and payload.retrieval != 'bm25':
                raise HTTPException(400, 'Private document search uses BM25.')
            if payload.generate and payload.profile == 'evidence_only':
                raise HTTPException(400, 'Select a local model profile to request generation.')
            filters = Filters(namespace=corpus_namespace, review_mode=payload.corpus, domain=payload.domain,
                              jurisdiction=payload.jurisdiction, state=payload.state or None, as_of=payload.as_of,
                              version_ids=payload.version_ids, include_superseded=payload.include_superseded)
            if payload.profile not in session.services:
                profile_settings = get_settings(payload.profile).model_copy(update={'data_dir': settings.data_dir})
                session.services[payload.profile] = ResearchService(registry, profile_settings)
            service = session.services[payload.profile]
            if payload.compare_private:
                authority = filters.model_copy(update={'namespace': 'official', 'review_mode': 'reviewed' if payload.corpus == 'reviewed' else 'demo',
                                                      'version_ids': payload.version_ids if corpus_namespace == 'official' else []})
                answer = service.inspect_private(payload.question, Filters(namespace=session.namespace, review_mode='private', domain=payload.domain), authority)
                scope_names = ['official', session.namespace]
            else:
                answer = service.answer(payload.question, filters, payload.retrieval, payload.generate)
                scope_names = [corpus_namespace]
            session.answer = answer
            session.answer_id = secrets.token_urlsafe(18)
            session.signatures = {name: registry.search_signature(name) for name in scope_names}
            data = answer.model_dump(mode='json')
            for hit, item in zip(answer.evidence, data['evidence']):
                item['reference'] = reference(hit)
                item['official_link'] = public_url(hit.source.official_url)
            return {**data, 'answer_id': session.answer_id}

    @app.get('/api/exports/{answer_id}')
    def export(answer_id: str, request: Request, format: Literal['markdown', 'json'] = 'markdown'):
        session = current(request)
        with guard:
            if not session.answer or answer_id != session.answer_id:
                raise HTTPException(404, 'Research record not found in this session.')
            if any(registry.search_signature(n) != sig for n, sig in session.signatures.items()):
                raise HTTPException(409, 'The corpus changed. Rerun the research before exporting.')
            content = export_markdown(session.answer) if format == 'markdown' else session.answer.model_dump_json(indent=2)
            suffix = 'md' if format == 'markdown' else 'json'
            return Response(content, media_type='text/markdown' if suffix == 'md' else 'application/json',
                            headers={'Content-Disposition': f'attachment; filename="vidhaan_research.{suffix}"'})

    @app.post('/api/private/upload')
    async def upload(request: Request):
        session = current(request)
        from .ingestion import ingest_bytes, safe_filename
        # Parse a single bounded file; authorization is checked before parsing.
        async with request.form(max_files=1, max_fields=1, max_part_size=1024) as form:
            file = form.get('file')
            if not file or not hasattr(file, 'read'):
                raise HTTPException(400, 'Choose one PDF, TXT or Markdown file.')
            domain = Domain(form.get('domain', Domain.employment.value))
            content = await file.read(settings.max_file_bytes + 1)
            if len(content) > settings.max_file_bytes or (file.size or 0) > settings.max_file_bytes:
                raise HTTPException(413, 'File exceeds the 25 MiB limit.')
            title = safe_filename(file.filename or '')
            source = Source(document_id='upload-' + hashlib.sha256(title.encode()).hexdigest()[:16], title=title,
                            domain=domain, namespace=session.namespace, instrument_type='private_document',
                            provenance_notes='User-uploaded facts, not legal authority')
            with guard:
                result = ingest_bytes(registry, content, title, source, settings.max_file_bytes)
                reset_answers()
            return {'version_id': result.version_id, 'created': result.created, 'chunks': result.chunks, 'warnings': result.warnings}

    @app.post('/api/private/clear')
    def clear_private(request: Request):
        session = current(request)
        with guard:
            registry.clear_private(session.namespace)
            session.services.clear()
            session.answer = None
            session.answer_id = None
        return {'status': 'cleared'}

    @app.post('/api/sources/{version_id}/review')
    def review(version_id: str, payload: ReviewRequest, request: Request):
        session = current(request)
        with guard:
            version = version_for(version_id, session)
            if version['namespace'] != 'official':
                raise HTTPException(400, 'Manual legal-source review applies only to official versions.')
            registry.review(version_id, payload.status, payload.notes, payload.verified_on)
            reset_answers()
        return {'status': 'recorded'}

    @app.post('/api/sources/{version_id}/exclude')
    def exclude(version_id: str, request: Request):
        session = current(request)
        with guard:
            version_for(version_id, session)
            registry.deactivate(version_id)
            reset_answers()
        return {'status': 'excluded'}

    @app.post('/api/corpus/{action}')
    def corpus_action(action: Literal['bundled', 'synthetic', 'acquire'], request: Request):
        current(request)
        with guard:
            if action == 'bundled':
                from .bundled import load_bundle
                result = load_bundle(registry, ROOT / 'data/bundled')
            elif action == 'synthetic':
                from .ingestion import ingest_file
                result = ingest_file(registry, ROOT / 'tests/fixtures/synthetic_employment.md',
                                     Source(document_id='synthetic-classroom', title='SYNTHETIC classroom employment fixture',
                                            domain=Domain.employment, namespace='synthetic'))
                result = {'chunks': result.chunks, 'created': result.created}
            else:
                from .sources import download_manifest
                result = download_manifest(registry, ROOT / 'data/registry/source_manifest.json')
            reset_answers()
            return result

    @app.get('/api/evaluation')
    def evaluation(request: Request):
        current(request)
        with guard:
            signature = registry.signature('official')
            candidates = [ROOT / 'evaluations/bundled/results.json', ROOT / 'evaluations/latest/results.json']
            reports = [json.loads(p.read_text()) for p in candidates if p.exists()]
            report = next((r for r in reports if r.get('corpus_signature') == signature), reports[-1] if reports else None)
            return {'report': report, 'matches_corpus': bool(report and report.get('corpus_signature') == signature)}

    @app.get('/api/diagnostics')
    def diagnostics(request: Request, profile: Literal['evidence_only', 'lenovo_cpu', 'mac_m5'] = 'evidence_only'):
        current(request)
        from .diagnostics import diagnose
        with guard:
            result = diagnose(get_settings(profile).model_copy(update={'data_dir': settings.data_dir}), registry)
            result['dense_snapshots'] = [s for s in result['dense_snapshots'] if s.get('namespace') in ('official', 'synthetic')]
            return result

    if (WEB / 'assets').is_dir():
        app.mount('/assets', StaticFiles(directory=WEB / 'assets'), name='assets')

    @app.get('/')
    def interface():
        if not (WEB / 'index.html').is_file():
            raise HTTPException(503, 'Web assets missing. Run npm ci and npm run build inside frontend.')
        return FileResponse(WEB / 'index.html', media_type='text/html', headers={'Cache-Control': 'no-cache'})

    return app
