# Configuration and ingestion

Copy `.env.example` to `.env`. `get_settings()` resolves project-relative `VIDHAAN_DATA_DIR` with pathlib. The local app has no secret or paid API requirement. Provider URL defaults to loopback. Never put personal credentials into sample configuration or a ZIP.

Profiles live in `configs/profiles.json`. All Settings fields can be overridden as `VIDHAAN_<UPPERCASE_FIELD>`; integer/boolean/path validation uses Pydantic. Some useful examples:

```dotenv
VIDHAAN_PROFILE=lenovo_cpu
VIDHAAN_MODEL=qwen3:4b
VIDHAAN_CONTEXT_TOKENS=4096
VIDHAAN_OUTPUT_TOKENS=512
VIDHAAN_EVIDENCE_TOKENS=1800
VIDHAAN_HISTORY_TOKENS=300
VIDHAAN_TOP_K=5
VIDHAAN_TIMEOUT_SECONDS=180
VIDHAAN_EMBEDDING_BATCH_SIZE=8
VIDHAAN_EMBEDDING_LOCAL_ONLY=true
VIDHAAN_VECTOR_BACKEND=auto
VIDHAAN_RERANK=false
```

`VIDHAAN_MODEL_CACHE` can point to a writable model cache (default `.cache/models`). Changing the model, its revision or tokenizer settings requires a new dense snapshot. The corpus survives independently. The base app is offline after dependency/source downloads; dense/reranking also require cached weights. Ollama generation contacts only the configured local server.

## Local official-document ingestion

Private UI uploads cannot silently become legal authorities. Import an actual downloaded official PDF using explicit metadata. This example is a schema template, **not an assertion that a legal document has been collected**:

```json
{
  "document_id": "your-stable-id",
  "title": "Actual title verified in your file",
  "domain": "Labour and employment",
  "namespace": "official",
  "instrument_type": null,
  "jurisdiction": "unknown",
  "states": [],
  "official_url": null,
  "effective_date": null,
  "review_status": "unreviewed",
  "provenance_notes": "Record actual acquisition and title checks here"
}
```

Save metadata to a local JSON file and run:

```bash
.venv/bin/python -m vidhaan.cli ingest 'path with spaces/official.pdf' --metadata metadata.json
```

Files must be valid PDF or UTF-8 TXT/Markdown, <=25 MiB. Encrypted, corrupt, empty/binary and excessively long files are rejected or flagged. Image-only documents retain originals but have no indexed text and need OCR. OCR is not implemented. A derivative OCR file needs its own checksum and provenance; never pretend it is the original extraction.

An explicit downloader manifest uses `allowed_hosts` and `sources` entries with `url`, `filename`, `title_check`, optional `expected_sha256`, and `metadata`. HTTPS scheme/host is checked at every redirect, files are bounded, content is parsed and the expected title must occur. The sample entries contain only observed official URLs and verified file hashes. Do not add unverified URLs or commercial legal databases. Fetch/index actions never grant legal review.

CLI review requires nonempty version-specific notes. `--verified-on` is needed before a reviewed version qualifies for Reviewed research:

```bash
.venv/bin/python -m vidhaan.cli review ACTUAL_VERSION_ID --status reviewed --notes 'Actual reviewer, scope, method and unresolved issues' --verified-on YYYY-MM-DD
```

This is a recording mechanism, not evidence that any review happened. All bundled sample inventory entries remain unreviewed. Rejected versions are excluded. Set `supersedes` to an actual prior version ID when a new version has an established relationship; do not infer legal repeal from a download date. `rechunk` and changed registry metadata invalidate vectors; refresh them explicitly.

## Optional reranking

```bash
.venv/bin/python -m pip install -r requirements-reranking.txt
.venv/bin/python -m vidhaan.cli cache-model --reranker
# Set VIDHAAN_RERANK=true only after weights are cached.
```

Candidate: `cross-encoder/ms-marco-MiniLM-L-6-v2`, CPU, local-only loading. Disabled on both default hardware profiles. The cloud did not download or benchmark this model. Scores are uncalibrated relevance values. CLI evaluation accepts the same settings, but compare a separately named result directory to avoid confusing reranked and baseline measurements.
