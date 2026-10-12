from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import sqlite3
from .models import Chunk, Domain, Source, utc_now


class Registry:
    """SQLite is authoritative. Index snapshots must match its corpus signature."""
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "registry" / "corpus.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS versions (
              version_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, namespace TEXT NOT NULL,
              checksum TEXT NOT NULL, metadata TEXT NOT NULL, raw_path TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1, indexed INTEGER NOT NULL DEFAULT 0,
              UNIQUE(namespace, document_id, checksum));
            CREATE TABLE IF NOT EXISTS chunks (
              chunk_id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES versions(version_id) ON DELETE CASCADE,
              kind TEXT NOT NULL, ordinal INTEGER NOT NULL, metadata TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS chunks_version ON chunks(version_id);
            CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL,
              action TEXT NOT NULL, version_id TEXT, details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT OR IGNORE INTO state VALUES ('revision','0');
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def bump(db):
        db.execute("UPDATE state SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")

    def add(self, source: Source, raw_path: Path, chunks: list[Chunk], active=True):
        with self.connection() as db:
            existing = db.execute("SELECT version_id FROM versions WHERE namespace=? AND document_id=? AND checksum=?",
                                  (source.namespace, source.document_id, source.checksum)).fetchone()
            if existing:
                return existing[0], False
            if source.supersedes:
                prior = db.execute("SELECT * FROM versions WHERE version_id=?", (source.supersedes,)).fetchone()
                if not prior or prior['document_id'] != source.document_id or prior['namespace'] != source.namespace:
                    raise ValueError("Supersedes must reference an existing version of this source and namespace")
                db.execute("UPDATE versions SET active=0 WHERE version_id=?", (source.supersedes,))
            db.execute("INSERT INTO versions VALUES (?,?,?,?,?,?,?,?)", (
                source.source_version, source.document_id, source.namespace, source.checksum,
                source.model_dump_json(), str(raw_path.relative_to(self.data_dir)), int(active), int(bool(chunks))))
            for chunk in chunks:
                db.execute("INSERT INTO chunks VALUES (?,?,?,?,?)", (chunk.chunk_id, chunk.version_id,
                           chunk.kind, chunk.ordinal, chunk.model_dump_json()))
            self.bump(db)
            self._audit(db, "ingest", source.source_version, {"chunks": len(chunks), "namespace": source.namespace})
        return source.source_version, True

    def versions(self, namespace: str | None = None):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM versions" + (" WHERE namespace=?" if namespace else "") + " ORDER BY document_id,version_id",
                              (namespace,) if namespace else ()).fetchall()
        return [dict(row, source=Source.model_validate_json(row['metadata'])) for row in rows]

    def chunks(self, version_id: str | None = None, kind="child") -> list[Chunk]:
        with self.connection() as db:
            rows = db.execute("SELECT metadata FROM chunks WHERE kind=?" + (" AND version_id=?" if version_id else "") +
                              " ORDER BY version_id,ordinal", (kind, version_id) if version_id else (kind,)).fetchall()
        return [Chunk.model_validate_json(row[0]) for row in rows]

    def chunk(self, chunk_id: str) -> Chunk | None:
        with self.connection() as db:
            row = db.execute("SELECT metadata FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
        return Chunk.model_validate_json(row[0]) if row else None

    def source(self, version_id: str) -> Source:
        with self.connection() as db:
            row = db.execute("SELECT metadata FROM versions WHERE version_id=?", (version_id,)).fetchone()
        if not row:
            raise KeyError(version_id)
        return Source.model_validate_json(row[0])

    def duplicate(self, namespace: str, checksum: str):
        return next((v for v in self.versions(namespace) if v['checksum'] == checksum), None)

    def signature(self, namespace: str | None = None):
        # Includes review and applicability metadata and deletions, not just raw bytes.
        records = [(v['version_id'], v['checksum'], v['metadata'], v['active'], v['indexed']) for v in self.versions(namespace)]
        records += [(c.chunk_id, c.model_dump_json()) for c in self.chunks() if namespace is None or c.namespace == namespace]
        return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()

    def review(self, version_id: str, status: str, notes: str, verified_on=None):
        if not notes.strip():
            raise ValueError("Manual review requires version-specific reviewer notes")
        source = self.source(version_id)
        previous = source.review_status
        source = Source.model_validate(dict(source.model_dump(), review_status=status,
                                           reviewer_notes=notes, last_verification_date=verified_on))
        with self.connection() as db:
            db.execute("UPDATE versions SET metadata=? WHERE version_id=?", (source.model_dump_json(), version_id))
            self.bump(db)
            self._audit(db, "manual_review", version_id, {"previous": previous, "status": status, "notes": notes})

    def search_signature(self, namespace='official'):
        prefix=hashlib.sha256(namespace.encode()).hexdigest()[:12]
        marker=self.data_dir/'indexes'/f'dense-{prefix}.json'
        index_hash=hashlib.sha256(marker.read_bytes()).hexdigest() if marker.is_file() else 'no-dense-snapshot'
        return hashlib.sha256((self.signature(namespace)+index_hash).encode()).hexdigest()

    def deactivate(self, version_id: str):
        with self.connection() as db:
            db.execute("UPDATE versions SET active=0 WHERE version_id=?", (version_id,))
            self.bump(db)
            self._audit(db, "supersede", version_id, {})

    def replace_chunks(self, version_id: str, chunks: list[Chunk], warnings=None):
        if any(c.version_id != version_id for c in chunks):
            raise ValueError('Chunk version mismatch')
        with self.connection() as db:
            db.execute('DELETE FROM chunks WHERE version_id=?', (version_id,))
            for chunk in chunks:
                db.execute('INSERT INTO chunks VALUES (?,?,?,?,?)',
                    (chunk.chunk_id, version_id, chunk.kind, chunk.ordinal, chunk.model_dump_json()))
            db.execute('UPDATE versions SET indexed=? WHERE version_id=?',(int(bool(chunks)),version_id))
            if warnings is not None:
                row=db.execute('SELECT metadata FROM versions WHERE version_id=?',(version_id,)).fetchone()
                source=Source.model_validate_json(row[0])
                source.extraction_warnings=warnings
                db.execute('UPDATE versions SET metadata=? WHERE version_id=?',(source.model_dump_json(),version_id))
            self.bump(db)
            self._audit(db,'rechunk',version_id,{'chunks':len(chunks)})

    def delete(self, version_id: str):
        with self.connection() as db:
            db.execute("DELETE FROM versions WHERE version_id=?", (version_id,))
            self.bump(db)
            self._audit(db, "delete", version_id, {})
        # Raw official originals remain for traceability; private clear removes its directory.

    def clear_private(self, namespace: str):
        if not namespace.startswith("private:"):
            raise ValueError("Only a private session can be cleared by this operation")
        for version in self.versions(namespace):
            path = (self.data_dir / version['raw_path']).resolve()
            private_root = (self.data_dir / "private").resolve()
            if path.is_relative_to(private_root):
                path.unlink(missing_ok=True)
            self.delete(version['version_id'])

    def coverage(self, namespace="official"):
        versions = self.versions(namespace)
        results = []
        for domain in Domain:
            rows = [v for v in versions if v['source'].domain == domain]
            results.append({"domain": domain.value, "sources": len({v['document_id'] for v in rows}),
                            "versions": len(rows), "collected": len(rows),
                            "parsed": sum(v['source'].parsing_status == 'parsed' for v in rows),
                            "indexed": sum(bool(v['indexed']) and bool(v['active']) for v in rows),
                            "reviewed": sum(v['source'].review_status == 'reviewed' for v in rows),
                            "states": sorted({s for v in rows for s in v['source'].states})})
        return results

    @staticmethod
    def _audit(db, action, version_id, details):
        # Default audit has no question text or private document content.
        db.execute("INSERT INTO audit(timestamp,action,version_id,details) VALUES (?,?,?,?)",
                   (utc_now(), action, version_id, json.dumps(details)))

    def audit_retrieval(self, ids, timings, filters, ranks):
        if filters.namespace.startswith("private:"):
            return  # Session-scoped private queries are not persisted.
        with self.connection() as db:
            self._audit(db, "retrieval", None, {"ids": ids, "timings": timings,
                        "filters": filters.model_dump(mode='json'), "ranks": ranks})
