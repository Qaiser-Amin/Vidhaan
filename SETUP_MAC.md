# macOS setup: Apple Silicon / M5 candidate target

Actual M5, macOS and Metal measurements have not been run. The later target has 24 GB unified memory; begin with evidence-only and measure before increasing model/context size.

Install Python 3.12 from python.org or `brew install python@3.12`. Extract the ZIP, then:

```bash
cd "$HOME/University Projects/vidhaan"
bash scripts/setup_mac.sh base
bash scripts/run_mac.sh evidence_only
```

Scripts validate the working directory and Python 3.12 and use `.venv/bin/python`. The launcher serves the included React interface using FastAPI; Node is not needed to run it. Open the local address printed by the server (default port 8765) in your browser. Setup needs the network; startup does not download packages or weights. The shell setup script was exercised on Linux with Python 3.12; native macOS is unperformed.

```bash
.venv/bin/python -m vidhaan.cli acquire
.venv/bin/python -m vidhaan.cli coverage
.venv/bin/python -m vidhaan.cli search 'wholesome drinking water in plantations'
```

Local runtime files remain on your machine; the ZIP includes only the 21 selected source documents with recorded reproduction terms and accompanying guides. Cached documents and installed dependencies allow offline BM25. The synthetic demo is a separate, labelled namespace.

## Optional models

```bash
bash scripts/setup_mac.sh embeddings
.venv/bin/python -m pip install -r requirements-faiss.txt  # optional
.venv/bin/python -m vidhaan.cli cache-model
.venv/bin/python -m vidhaan.cli index-dense
.venv/bin/python -m vidhaan.cli search 'drinking water' --mode dense
```

macOS uses PyPI's native PyTorch wheel; the Windows/Linux CPU-only wheel selector does not apply. Python embeddings explicitly use CPU for portability. FAISS is optional, with a reported NumPy fallback if native installation is unavailable. Hugging Face dependencies/weights are initial downloads only; local-only loading is the normal mode.

Install Ollama's official macOS application or `brew install ollama` and start its local server using the distribution's instructions. Do not assume a running server merely because its CLI is installed.

```bash
ollama pull qwen3:4b                 # retained smaller option
# Optional larger candidate, only if this tag is available:
ollama pull qwen3.5:9b
ollama list
.venv/bin/python -m vidhaan.cli --profile mac_m5 diagnostics
bash scripts/run_mac.sh mac_m5
```

Ollama can use Metal on supported Apple Silicon builds; inspect `ollama ps` while it runs to verify actual acceleration. No M5 speed or superiority is promised. The app starts with an 8,192 total-context profile, one generation at a time, bounded evidence/history/output, and disabled thinking. For the smaller model, copy `.env.example` to `.env` and set `VIDHAAN_MODEL=qwen3:4b`.

```bash
cp .env.example .env
# Edit .env locally; no secrets are required.
```

## Reproduce evaluation

```bash
bash scripts/setup_mac.sh dev
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_benchmark.py
.venv/bin/python -m vidhaan.cli evaluate --split development --output evaluations/development --modes bm25
.venv/bin/python -m vidhaan.cli evaluate --output evaluations/latest
.venv/bin/python scripts/package_project.py
```

Acquire before building benchmark IDs. If dense indexing changes child boundaries, regenerate and inspect labels first. Record your real hardware, model tag, latency and memory; generation tokens/second require actual Ollama token counts and generation duration, not total wall time. Human semantic/legal scores stay pending until reviewed. Optional reranking is described in `docs/CONFIGURATION.md` and should be benchmarked, not enabled to imply legal confidence.

If a wheel is missing, retain base mode and NumPy vector search. If model weights are missing, dense-only reports unavailable and hybrid explicitly uses BM25. If Ollama/models time out or return malformed output, exact extracts remain visible. Verify local server/selected model and use a smaller candidate before expanding budgets.

## Included corpus

The final ZIP contains 21 source documents across all eight domains. Setup and launch load them offline with checksum checks; first loading builds the local text index. Repeat loads preserve review and excluded/newer versions. Two Labour Ministry FAQs remain optional online downloads under their source terms. Use Workspace settings → Load project documents offline for direct Python startup. See `docs/CORPUS_REUSE.md` for attribution and reproduction records.
