"""Optional CPU embedding snapshots. Model weights are never downloaded implicitly."""
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import os
import time
import uuid
import numpy as np
from .chunking import chunk_pages, Page, CHUNKER_VERSION
from .models import Source


class IndexUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=2)
def load_embedding(model: str, local_only=True, revision=None):
    try:
        from sentence_transformers import SentenceTransformer
        from huggingface_hub import snapshot_download
        from .config import ROOT
        # Require the published SentenceTransformers architecture, not its implicit
        # generic mean-pooling fallback. Download only this small model's needed files.
        cache = os.getenv('VIDHAAN_MODEL_CACHE', str(ROOT / '.cache' / 'models'))
        snapshot = Path(snapshot_download(repo_id=model, revision=revision, local_files_only=local_only,
            cache_dir=cache, allow_patterns=['modules.json','config_sentence_transformers.json',
            'sentence_bert_config.json','config.json','tokenizer*.json','special_tokens_map.json',
            'vocab.txt','model.safetensors','1_Pooling/config.json']))
        for filename in ('modules.json','config.json','model.safetensors'):
            if not (snapshot / filename).is_file():
                raise OSError(f'Incomplete published embedding snapshot: {filename} missing')
        encoder = SentenceTransformer(str(snapshot), device='cpu', local_files_only=True)
        encoder._vidhaan_revision = snapshot.name
        return encoder
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise IndexUnavailable("Embedding model unavailable. Install requirements-embeddings.txt and explicitly run "
                               "'python -m vidhaan.cli cache-model'. BM25 still works.") from exc


def model_identity(model, settings):
    config = getattr(model[0].auto_model, 'config', None)
    resolved = getattr(model, '_vidhaan_revision', None) or getattr(config, '_commit_hash', None)
    return {'name': settings.embedding_model, 'revision': resolved or settings.embedding_revision,
            'dimension': model.get_sentence_embedding_dimension(), 'max_sequence_length': model.max_seq_length}


def atomic_json(path: Path, value):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def _prefix(namespace):
    return hashlib.sha256(namespace.encode()).hexdigest()[:12]


def build_dense(registry, settings, namespace='official', model=None):
    if namespace.startswith('private:'):
        raise IndexUnavailable("Persistent dense indexing of private sessions is disabled; use private BM25")
    model = model or load_embedding(settings.embedding_model, settings.embedding_local_only, settings.embedding_revision)
    identity = model_identity(model, settings)
    limit = min(384, int(model.max_seq_length))
    # Retain section parents. Replace only children that exceed the real tokenizer limit.
    for version in registry.versions(namespace):
        old = registry.chunks(version['version_id'])
        if not old or all(len(model.tokenizer.encode(c.text, add_special_tokens=True, truncation=False)) <= limit for c in old):
            continue
        # Re-read the preserved original to retain exact physical page offsets.
        from .ingestion import extract
        raw_path = registry.data_dir / version['raw_path']
        pages, _ = extract(raw_path.read_bytes(), raw_path.suffix.lower())
        new = [c for c in chunk_pages(pages, version['source'], tokenizer=model.tokenizer, limit=limit) if c.kind=='child']
        with registry.connection() as db:
            db.execute("DELETE FROM chunks WHERE version_id=? AND kind='child'", (version['version_id'],))
            for child in new:
                db.execute("INSERT INTO chunks VALUES (?,?,?,?,?)", (child.chunk_id, child.version_id,
                    'child', child.ordinal, child.model_dump_json()))
            registry.bump(db)
    chunks = [c for c in registry.chunks() if c.namespace == namespace]
    if not chunks:
        raise IndexUnavailable('No parsed chunks in this namespace')
    signature = registry.signature(namespace)
    directory = registry.data_dir / 'indexes'
    directory.mkdir(exist_ok=True)
    marker = directory / f'dense-{_prefix(namespace)}.json'
    previous = None
    previous_vectors = None
    if marker.exists():
        try:
            candidate = json.loads(marker.read_text())
            if candidate['identity'] == identity:
                path = directory / candidate['vectors_file']
                if path.resolve().is_relative_to(directory.resolve()) and hashlib.sha256(path.read_bytes()).hexdigest() == candidate['vectors_checksum']:
                    previous = candidate
                    previous_vectors = np.load(path, allow_pickle=False)
                    if previous_vectors.shape != (len(candidate['chunk_ids']),identity['dimension']) or not np.isfinite(previous_vectors).all():
                        previous=None
                        previous_vectors=None
        except (ValueError, OSError, KeyError):
            pass
    reusable = {cid: previous_vectors[i] for i, cid in enumerate(previous['chunk_ids'])} if previous else {}
    missing = [c for c in chunks if c.chunk_id not in reusable]
    start = time.perf_counter()
    for offset in range(0, len(missing), settings.embedding_batch_size):
        batch = missing[offset:offset + settings.embedding_batch_size]
        if any(len(model.tokenizer.encode(c.text, add_special_tokens=True, truncation=False)) > model.max_seq_length for c in batch):
            raise IndexUnavailable('Tokenizer limit violation: refused to truncate evidence')
        vectors = model.encode([c.text for c in batch], batch_size=settings.embedding_batch_size,
                               normalize_embeddings=True, show_progress_bar=False)
        reusable.update({c.chunk_id: v for c, v in zip(batch, vectors)})
    matrix = np.asarray([reusable[c.chunk_id] for c in chunks], dtype=np.float32)
    if matrix.shape != (len(chunks), identity['dimension']) or not np.isfinite(matrix).all():
        raise IndexUnavailable('Model produced invalid dimensions or non-finite vectors')
    filename = f'dense-{_prefix(namespace)}-{uuid.uuid4().hex}.npy'
    path = directory / filename
    np.save(path, matrix, allow_pickle=False)
    metadata = {'format_version': 1, 'chunker_version': CHUNKER_VERSION, 'namespace': namespace,
        'corpus_signature': signature, 'identity': identity, 'chunk_ids': [c.chunk_id for c in chunks],
        'source_checksums': {c.version_id: c.source_checksum for c in chunks}, 'vectors_file': filename,
        'vectors_checksum': hashlib.sha256(path.read_bytes()).hexdigest(), 'normalized': True,
        'build_seconds': time.perf_counter() - start, 'new_chunks': len(missing), 'reused_chunks': len(chunks)-len(missing)}
    if registry.signature(namespace) != signature:
        path.unlink(missing_ok=True)
        raise IndexUnavailable('Corpus changed during indexing; rerun to reuse the previous snapshot')
    atomic_json(marker, metadata)  # Manifest replacement is the commit point.
    if previous and previous.get('vectors_file') != filename:
        (directory / previous['vectors_file']).unlink(missing_ok=True)
    return metadata


class DenseIndex:
    def __init__(self, registry, settings, namespace, model=None):
        marker = registry.data_dir / 'indexes' / f'dense-{_prefix(namespace)}.json'
        if not marker.is_file():
            raise IndexUnavailable('Dense snapshot missing. Cache the embedding weights, then run index-dense; BM25 remains available.')
        self.model = model or load_embedding(settings.embedding_model, settings.embedding_local_only, settings.embedding_revision)
        try:
            self.metadata = json.loads(marker.read_text())
            if self.metadata['corpus_signature'] != registry.signature(namespace):
                raise IndexUnavailable('Dense index is stale after corpus/review/version changes; run index-dense')
            if self.metadata['identity'] != model_identity(self.model, settings):
                raise IndexUnavailable('Dense model identity or dimensions mismatch; rebuild index')
            path = marker.parent / self.metadata['vectors_file']
            if not path.resolve().is_relative_to(marker.parent.resolve()):
                raise IndexUnavailable('Unsafe vector file path')
            if hashlib.sha256(path.read_bytes()).hexdigest() != self.metadata['vectors_checksum']:
                raise IndexUnavailable('Vector checksum mismatch; rebuild index')
            self.vectors = np.load(path, allow_pickle=False)
            if self.vectors.shape != (len(self.metadata['chunk_ids']), self.metadata['identity']['dimension']):
                raise IndexUnavailable('Index dimensions mismatch')
            self.positions = {cid: i for i, cid in enumerate(self.metadata['chunk_ids'])}
            if len(self.positions) != len(self.vectors) or not np.isfinite(self.vectors).all():
                raise IndexUnavailable('Corrupt or duplicate index entries')
            for chunk in registry.chunks():
                if chunk.namespace == namespace and (chunk.chunk_id not in self.positions or
                    self.metadata['source_checksums'].get(chunk.version_id) != chunk.source_checksum):
                    raise IndexUnavailable('SQLite/index content mismatch')
        except (OSError, ValueError, KeyError) as exc:
            raise IndexUnavailable('Dense snapshot missing or corrupt; run index-dense') from exc
        self.backend = settings.vector_backend
        if self.backend == 'auto':
            import importlib.util
            self.backend = 'faiss' if importlib.util.find_spec('faiss') else 'numpy (FAISS unavailable)'

    def rank(self, question, eligible, limit):
        # Scope is applied BEFORE ranking, including in the FAISS path.
        selected = [c for c in eligible if c.chunk_id in self.positions]
        if not selected:
            return []
        matrix = self.vectors[[self.positions[c.chunk_id] for c in selected]]
        query = self.model.encode(['Represent this sentence for searching relevant passages: ' + question],
                                  normalize_embeddings=True, show_progress_bar=False)[0].astype(np.float32)
        if query.shape != (matrix.shape[1],):
            raise IndexUnavailable('Query vector dimension mismatch')
        if self.backend == 'faiss':
            try:
                import faiss
                index = faiss.IndexFlatIP(matrix.shape[1])
                index.add(matrix)
                values, positions = index.search(query.reshape(1, -1), min(limit, len(selected)))
                return [(selected[i], float(score)) for i, score in zip(positions[0], values[0]) if i >= 0]
            except ImportError:
                self.backend = 'numpy (FAISS unavailable)'
        scores = matrix @ query
        order = np.argsort(-scores, kind='stable')[:limit]
        return [(selected[i], float(scores[i])) for i in order]
