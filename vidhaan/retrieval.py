from functools import lru_cache
import hashlib
import json
import re
import time
from rank_bm25 import BM25Plus
from .indexing import DenseIndex, IndexUnavailable, atomic_json
from .models import Filters, Hit, Source
from .tokenization import STOP, normalize, tokenize


def eligible(source: Source, active: bool, filters: Filters) -> bool:
    if source.namespace != filters.namespace:
        return False
    if filters.review_mode == 'synthetic' and source.namespace != 'synthetic':
        return False
    if filters.review_mode != 'synthetic' and source.namespace == 'synthetic':
        return False
    if source.namespace.startswith('private:') and filters.review_mode != 'private':
        return False
    if filters.review_mode == 'reviewed' and (source.review_status != 'reviewed' or source.last_verification_date is None):
        return False
    if source.review_status == 'rejected':
        return False
    if not active and not filters.include_superseded:
        return False
    if filters.domain and not source.allows_domain(filters.domain):
        return False
    if filters.jurisdiction and source.jurisdiction != filters.jurisdiction:
        return False
    if filters.state and source.jurisdiction == 'state' and filters.state not in source.states:
        return False
    if filters.state and source.jurisdiction == 'unknown':
        return False
    if filters.version_ids and source.source_version not in filters.version_ids:
        return False
    if filters.as_of:
        if source.effective_date is None or source.effective_date > filters.as_of:
            return False
        if source.effective_until and source.effective_until < filters.as_of:
            return False
    return source.parsing_status == 'parsed'


@lru_cache(maxsize=16)
def lexical_model(token_documents):
    return BM25Plus([list(tokens) or ['__empty__'] for tokens in token_documents], delta=0)


def bm25_rank(question, chunks, limit, min_terms=1, token_map=None):
    terms = tokenize(question)
    if not terms or not chunks:
        return []
    tokens = tuple(tuple(token_map[c.chunk_id]) if token_map is not None else tuple(tokenize(c.text)) for c in chunks)
    scores = lexical_model(tokens).get_scores(terms)
    candidates = [(chunk, float(score)) for chunk, score, words in zip(chunks, scores, tokens)
                  if len(set(terms) & set(words)) >= min_terms and score > 0]
    return sorted(candidates, key=lambda item: (-item[1], item[0].chunk_id))[:limit]


def rrf(rankings, k=60):
    merged = {}
    for backend, ranking in rankings.items():
        for rank, (chunk, _) in enumerate(ranking, 1):
            entry = merged.setdefault(chunk.chunk_id, [chunk, 0.0, {}])
            entry[1] += 1 / (k + rank)
            entry[2][backend] = rank
    return sorted(merged.values(), key=lambda item: (-item[1], item[0].chunk_id))


@lru_cache(maxsize=1)
def load_reranker(name):
    try:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(name, device='cpu', local_files_only=True)
    except (ImportError, OSError, ValueError) as exc:
        raise IndexUnavailable('Optional reranker unavailable. Explicitly cache its weights first.') from exc


class Retriever:
    def __init__(self, registry, settings, dense_factory=DenseIndex):
        self.registry = registry
        self.settings = settings
        self.dense_factory = dense_factory
        self.last_diagnostics = {}

    def search(self, question, filters=None, mode='bm25', limit=None):
        if mode not in ('bm25', 'dense', 'hybrid'):
            raise ValueError('Retrieval mode must be bm25, dense or hybrid')
        filters = filters or Filters()
        private_dense = filters.namespace.startswith('private:') and mode in ('dense','hybrid')
        if private_dense and mode == 'dense':
            raise IndexUnavailable('Private sessions use BM25; persistent private dense indexes are intentionally disabled.')
        question = normalize(question)
        limit = limit or self.settings.top_k
        start = time.perf_counter()
        versions = {v['version_id']: v for v in self.registry.versions(filters.namespace)}
        allowed = {vid for vid,v in versions.items() if eligible(v['source'], bool(v['active']), filters)}
        all_chunks = self.registry.chunks(namespace=filters.namespace)
        chunks = [c for c in all_chunks if c.version_id in allowed
                  and c.content_role != 'contents'
                  and (not filters.domain or versions[c.version_id]['source'].includes_passage(c, filters.domain))
                  and (not filters.jurisdiction or c.jurisdiction == filters.jurisdiction)
                  and (not filters.state or c.jurisdiction != 'unknown')]
        diagnostics = {'mode': mode, 'eligible_versions': len(allowed), 'eligible_chunks': len(chunks), 'warnings': []}
        if private_dense:
            diagnostics['warnings'].append('Private session: using BM25, with no private dense snapshot persisted.')
            diagnostics['mode'] = 'bm25 (private hybrid unavailable)'
        candidate_limit = min(50, limit * 4)
        rankings = {}
        if mode in ('bm25', 'hybrid'):
            token_map = None
            if filters.namespace == 'official':
                from .lexical import ensure_domain
                domains = [filters.domain] if filters.domain else sorted({c.domain for c in chunks})
                token_map = {}
                for domain in domains:
                    mapped, _ = ensure_domain(self.registry, domain, list(versions.values()), all_chunks)
                    token_map.update(mapped)
                # Explicit historical comparison may include excluded versions.
                for chunk in chunks:
                    if chunk.chunk_id not in token_map: token_map[chunk.chunk_id] = tuple(tokenize(chunk.text))
                diagnostics['lexical_index'] = 'checksum-checked official domain indexes'
            rankings['bm25'] = bm25_rank(question, chunks, candidate_limit, self.settings.min_lexical_terms, token_map)
            if filters.namespace == 'synthetic':
                # Persist only safe namespace tokens, never private text/questions.
                path = self.registry.data_dir / 'indexes' / ('bm25-' + hashlib.sha256(filters.namespace.encode()).hexdigest()[:12] + '.json')
                signature = self.registry.signature(filters.namespace)
                try:
                    old = json.loads(path.read_text())
                except (OSError, ValueError):
                    old = {}
                if old.get('signature') != signature:
                    all_chunks = [c for c in self.registry.chunks() if c.namespace == filters.namespace]
                    atomic_json(path, {'signature': signature, 'backend': 'rank_bm25.BM25Plus',
                                      'chunks': {c.chunk_id: tokenize(c.text) for c in all_chunks}})
        if mode in ('dense', 'hybrid') and chunks and not private_dense:
            try:
                index = self.dense_factory(self.registry, self.settings, filters.namespace)
                rankings['dense'] = index.rank(question, chunks, candidate_limit)
                diagnostics['vector_backend'] = index.backend
            except IndexUnavailable as exc:
                if mode == 'dense':
                    raise
                diagnostics['warnings'].append(str(exc))
                diagnostics['mode'] = 'bm25 (hybrid unavailable)'
        merged = rrf(rankings)
        if self.settings.rerank and merged:
            reranker = load_reranker(self.settings.reranker_model)
            scores = reranker.predict([[question, item[0].text] for item in merged])
            merged = [item for _, item in sorted(zip(scores, merged), key=lambda pair: -pair[0])]
            diagnostics['reranked'] = True
        hits = []
        by_parent = {}
        for chunk in chunks:
            by_parent.setdefault(chunk.parent_id, []).append(chunk)
        for chunk, score, ranks in merged[:limit]:
            siblings = by_parent.get(chunk.parent_id, [])
            neighbors = [c for c in siblings if abs(c.ordinal-chunk.ordinal) <= 1 and c.chunk_id != chunk.chunk_id]
            parent = self.registry.chunk(chunk.parent_id) if chunk.parent_id else None
            # Parents are available in the source viewer. Only adjacent exact children go into generation.
            hits.append(Hit(chunk=chunk, source=versions[chunk.version_id]['source'], score=score, ranks=ranks,
                            context=neighbors))
        diagnostics['retrieval_seconds'] = time.perf_counter()-start
        self.last_diagnostics = diagnostics
        self.registry.audit_retrieval([h.chunk.chunk_id for h in hits], {'retrieval_seconds': diagnostics['retrieval_seconds']},
                                     filters, {h.chunk.chunk_id:h.ranks for h in hits})
        return hits
