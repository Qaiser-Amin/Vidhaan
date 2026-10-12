"""Portable official-domain inverted indexes; SQLite remains authoritative.

Persist postings and source/chunk fingerprints, not pickles or private content.
Eligibility is still applied before fitting BM25, so excluded/reviewed/date scopes
never borrow document frequencies from ineligible material.
"""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import hashlib
import json
from .indexing import atomic_json
from .models import Domain
from .tokenization import TOKENIZER, tokenize

BACKEND = 'rank_bm25.BM25Plus'


def filename(domain):
    return 'bm25-' + Domain(domain).name + '.json'


def snapshot(domain, versions, chunks):
    domain = Domain(domain)
    selected = {v['version_id']: v for v in versions if v['source'].namespace == 'official'
                and v['source'].allows_domain(domain) and v['active'] and v['indexed']}
    rows = sorted((c for c in chunks if c.namespace == 'official' and c.version_id in selected
                   and c.kind == 'child' and c.content_role != 'contents'
                   and selected[c.version_id]['source'].includes_passage(c, domain)), key=lambda c: c.chunk_id)
    used = {c.version_id for c in rows}
    sources = [{'document_id': v['document_id'], 'version_id': vid, 'sha256': v['checksum']}
               for vid, v in sorted(selected.items()) if vid in used]
    hashes = [hashlib.sha256(c.model_dump_json().encode()).hexdigest() for c in rows]
    signature = hashlib.sha256(json.dumps({'tokenizer': TOKENIZER, 'domain': domain.value,
                                           'sources': sources, 'chunk_hashes': hashes}, sort_keys=True).encode()).hexdigest()
    return rows, sources, hashes, signature


def payload(domain, versions, chunks):
    rows, sources, hashes, signature = snapshot(domain, versions, chunks)
    postings, lengths = {}, []
    for number, chunk in enumerate(rows):
        terms = Counter(tokenize(chunk.text))
        lengths.append(sum(terms.values()))
        for term, count in sorted(terms.items()):
            postings.setdefault(term, []).append([number, count])
    return {'schema_version': 1, 'namespace': 'official', 'domain': Domain(domain).value,
            'backend': BACKEND, 'tokenizer': TOKENIZER, 'signature': signature,
            'sources': sources, 'chunk_ids': [c.chunk_id for c in rows], 'chunk_hashes': hashes,
            'document_lengths': lengths, 'postings': postings,
            'ranking': {'delta': 0, 'k1': 1.5, 'b': 0.75},
            'note': 'Exact source text stays in SQLite/original files. Review/date/jurisdiction eligibility is applied before BM25 scoring.'}


def check_shape(data, domain=None):
    if data.get('schema_version') != 1 or data.get('namespace') != 'official' or data.get('backend') != BACKEND or data.get('tokenizer') != TOKENIZER:
        raise ValueError('Unsupported official lexical index')
    actual_domain = Domain(data['domain'])
    if domain is not None and actual_domain != Domain(domain): raise ValueError('Lexical index domain mismatch')
    ids = data['chunk_ids']
    if not isinstance(ids, list) or len(ids) > 100000 or len(ids) != len(set(ids)):
        raise ValueError('Invalid lexical chunk IDs')
    if len(data['chunk_hashes']) != len(ids) or len(data['document_lengths']) != len(ids):
        raise ValueError('Lexical index arrays differ')
    if data.get('ranking') != {'delta': 0, 'k1': 1.5, 'b': 0.75}: raise ValueError('Unexpected lexical ranking configuration')
    if not isinstance(data['postings'], dict) or len(data['postings']) > 500000:
        raise ValueError('Invalid lexical postings')
    if any(not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 20000 for n in data['document_lengths']):
        raise ValueError('Invalid lexical document lengths')
    return actual_domain


def token_documents(data):
    check_shape(data)
    terms = [Counter() for _ in data['chunk_ids']]
    for term, positions in data['postings'].items():
        if not isinstance(term, str) or tokenize(term) != [term] or not isinstance(positions, list):
            raise ValueError('Invalid lexical term')
        seen = set()
        for position in positions:
            if not isinstance(position, list) or len(position) != 2: raise ValueError('Invalid lexical posting')
            number, count = position
            if not isinstance(number, int) or isinstance(number, bool) or not 0 <= number < len(terms) or number in seen:
                raise ValueError('Invalid lexical posting document')
            if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 20000:
                raise ValueError('Invalid lexical frequency')
            seen.add(number); terms[number][term] = count
    if [sum(t.values()) for t in terms] != data['document_lengths']: raise ValueError('Lexical lengths differ from postings')
    return {cid: tuple(word for word, count in sorted(counter.items()) for _ in range(count))
            for cid, counter in zip(data['chunk_ids'], terms)}


@lru_cache(maxsize=16)
def checked_tokens(serialized, signature, chunk_texts):
    data = json.loads(serialized)
    if data['signature'] != signature: raise ValueError('Stale lexical signature')
    tokens = token_documents(data)
    if set(tokens) != {cid for cid, _ in chunk_texts}: raise ValueError('Lexical chunk set differs')
    for cid, text in chunk_texts:
        if Counter(tokens[cid]) != Counter(tokenize(text)): raise ValueError('Lexical tokens differ from source text')
    return tokens


def ensure_domain(registry, domain, versions=None, chunks=None, bundled_path=None):
    versions = versions if versions is not None else registry.versions('official')
    chunks = chunks if chunks is not None else registry.chunks(namespace='official')
    rows, sources, hashes, signature = snapshot(domain, versions, chunks)
    path = registry.data_dir / 'indexes' / filename(domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = None
    for candidate in [path, *([Path(bundled_path)] if bundled_path else [])]:
        try:
            if candidate.is_symlink() or candidate.stat().st_size > 25 * 1024 * 1024: continue
            content = candidate.read_text()
            data = json.loads(content); check_shape(data, domain)
            if data['signature'] != signature or data['sources'] != sources or data['chunk_hashes'] != hashes or data['chunk_ids'] != [c.chunk_id for c in rows]: continue
            tokens = checked_tokens(content, signature, tuple((c.chunk_id, c.text) for c in rows))
            if candidate != path: atomic_json(path, data)
            serialized = content
            break
        except (OSError, ValueError, KeyError, TypeError): continue
    if serialized is None:
        data = payload(domain, versions, chunks)
        atomic_json(path, data)
        serialized = path.read_text()
        tokens = checked_tokens(serialized, signature, tuple((c.chunk_id, c.text) for c in rows))
    return tokens, {'domain': Domain(domain).value, 'file': path.name, 'sources': len(sources),
                    'chunks': len(rows), 'signature': signature, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def build_all(registry, bundled_paths=None):
    versions = registry.versions('official'); chunks = registry.chunks(namespace='official')
    return [ensure_domain(registry, d, versions, chunks, (bundled_paths or {}).get(d.value))[1] for d in Domain]
