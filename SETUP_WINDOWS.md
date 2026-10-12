# Windows setup: Lenovo X1 Carbon

Python 3.12, Windows 10/11, 16 GB RAM target. Actual Windows/hardware timing has not been measured. Start with BM25 and no LLM; add optional components individually.

1. Install Python 3.12 from python.org with the Python launcher. Extract the ZIP to a writable folder.
2. Open PowerShell. Quote paths containing spaces:

```powershell
Set-Location 'C:\Users\YourName\University Projects\vidhaan'
# Only if PowerShell blocks local downloaded scripts; affects this shell only:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1 -Profile base
.\scripts\run_windows.ps1 -Profile evidence_only
```

Setup validates its project location and Python version, creates `.venv`, installs pinned requirements and checks dependencies. Run always uses `.venv\Scripts\python.exe`. You do not need environment activation. Normal startup has no dependency/model downloads. The launcher serves the included React interface using FastAPI. Open the local address printed by the server (default port 8765) in your browser; Node is not required.

Setup loads the included corpus offline. Validate source-based evidence, or explicitly acquire additional/updated official samples online:

```powershell
.\.venv\Scripts\python.exe -m vidhaan.cli acquire
.\.venv\Scripts\python.exe -m vidhaan.cli coverage
.\.venv\Scripts\python.exe -m vidhaan.cli search 'wholesome drinking water in plantations'
```

Download/type/title/checksum failures are actionable errors. Do not replace an expected checksum to make it pass; inspect an actual new official version first. If government sites are inaccessible, import a downloaded official file with explicit source metadata using the CLI, or use the separate synthetic demo. The final ZIP starts with 21 included sources; an empty source-only checkout has no coverage until sources are imported.

## Optional CPU embeddings and generation

```powershell
.\scripts\setup_windows.ps1 -Profile embeddings
# Optional native vector backend; leave it out if no compatible wheel exists:
.\.venv\Scripts\python.exe -m pip install -r requirements-faiss.txt
.\.venv\Scripts\python.exe -m vidhaan.cli cache-model
.\.venv\Scripts\python.exe -m vidhaan.cli index-dense
.\.venv\Scripts\python.exe -m vidhaan.cli search 'drinking water' --mode hybrid
```

The CPU wheel index is included in the embeddings requirements. No CUDA toolkit, GPU, TensorFlow or paid service is required. The small BGE weights are a one-time download into `.cache/models` (unbundled); local-only loading is the default afterward. Native FAISS failures do not prevent NumPy cosine search. Dense-only never silently becomes BM25; hybrid fallback is explicitly reported.

Install Ollama from its official Windows installer. Start it, then:

```powershell
ollama pull qwen3:4b
ollama list
.\.venv\Scripts\python.exe -m vidhaan.cli --profile lenovo_cpu diagnostics
.\scripts\run_windows.ps1 -Profile lenovo_cpu
```

Enable local generation in the UI only after the server and selected model are available. The default URL is `http://127.0.0.1:11434`. The application does not connect to this laptop from the Codex cloud. Qwen3 4b is a configurable candidate, with thinking disabled and one request at a time; speed and answer quality require measurement. The full context includes instructions, quotes, history and output, not 4,096 evidence tokens alone.

To edit local settings without secrets:

```powershell
Copy-Item .env.example .env
notepad .env
```

Use `VIDHAAN_MODEL`, `VIDHAAN_CONTEXT_TOKENS`, `VIDHAAN_OUTPUT_TOKENS`, `VIDHAAN_EVIDENCE_TOKENS`, `VIDHAAN_TOP_K` and `VIDHAAN_TIMEOUT_SECONDS`. Change all budgets consistently; impossible totals fail validation.

## Tests, evaluation and packaging

```powershell
.\scripts\setup_windows.ps1 -Profile dev
.\.venv\Scripts\python.exe -m pytest -q
# Acquire the official sample first; re-author IDs if chunking changes:
.\.venv\Scripts\python.exe scripts\build_benchmark.py
.\.venv\Scripts\python.exe -m vidhaan.cli evaluate --split development --output evaluations\development --modes bm25
.\.venv\Scripts\python.exe -m vidhaan.cli evaluate
.\.venv\Scripts\python.exe scripts\package_project.py
```

`dist\Vidhaan_University_RAG.zip` excludes your private files, `.env`, `.venv`, Git metadata, models and raw legal PDFs. A dev run with no FAISS skips only its optional native-backend test. Fixture/model mocks are labelled engineering tests, not legal accuracy measurements.

Troubleshooting: missing `py -3.12` means Python/launcher installation; missing FastAPI/Uvicorn means rerun base setup; memory pressure means smaller model, bounded context, no reranking and small embedding batches; scanned PDFs need external OCR with a newly identified derivative source, not pretend extraction. Proxy errors need access to the listed government/model hosts; never disable TLS verification. An official PDF changed on the server needs a new inspected manifest/version. `BUILD_STATUS.md` records the cloud evidence, not a Windows certification.

## Included corpus

The final ZIP contains 21 source documents across all eight domains. Setup and launch load them offline with checksum checks; first loading builds the local text index. Repeat loads preserve review and excluded/newer versions. Two Labour Ministry FAQs remain optional online downloads under their source terms. Use Workspace settings → Load project documents offline for direct Python startup. See `docs/CORPUS_REUSE.md` for attribution and reproduction records.
