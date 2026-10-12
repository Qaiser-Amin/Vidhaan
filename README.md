# VIDHAAN

**Author: Qaiser Amin Ganaie.** A Python 3.12, local, single-user Indian legal research university project with a custom **React + FastAPI** interface. It uses retrieval-augmented generation when local models are available and real BM25 retrieval with verbatim evidence when they are not. There are no paid API, database or hosting requirements.

The interface includes a responsive research workspace, animated domain cards, evidence readers, searchable sources, coverage and evaluation screens, and private uploads. It has self-hosted fonts, keyboard controls and reduced-motion support. **Streamlit has been removed.** The compiled interface is included; Node is needed only to develop it.

## Start on your laptop

Extract `Vidhaan_University_RAG.zip`. Its single top-level folder is `vidhaan`.

Windows PowerShell:

```powershell
Set-Location 'C:\Your Folder\vidhaan'
.\scripts\setup_windows.ps1
.\scripts\run_windows.ps1
```

macOS (also tested on Linux with Python 3.12):

```bash
cd "$HOME/Your Folder/vidhaan"
bash scripts/setup_mac.sh
bash scripts/run_mac.sh
```

If Windows blocks local scripts, use the process-only execution-policy command in [SETUP_WINDOWS.md](SETUP_WINDOWS.md). Launch uses `.venv` and downloads nothing. Setup uses the network to install dependencies. Open the local address printed by the server in your laptop browser; the default port is **8765**. Do not expose this prototype to the public internet.

## Actual coverage and first official workflow

The final project includes **21 official-host documents across all eight domains, yielding 5,786 official child passages; zero legally reviewed versions**. Setup and launch scripts load the included corpus locally, so normal research needs no source download. The sources come from the Ministry of Labour, Ministry of Home Affairs and Income Tax Department. See the [eight domain guides](docs/domains/README.md), [source inventory](DATA_SOURCES.md) and [reproduction records](docs/CORPUS_REUSE.md).

The cloud acquisition contains 23 sources and 5,819 passages. Two Labour Ministry FAQs require reproduction permission and remain optional downloads; the final ZIP includes the other 21 sources.

| Domain | Indexed sources |
|---|---:|
| Labour and employment | 3 |
| Consumer law | 1 |
| Contracts | 3 |
| Tenancy and property | 2 |
| Family law | 2 |
| Criminal and civil procedure | 4 |
| Corporate and tax | 3 |
| Other specialist areas | 3 |

Every domain has representative material; coverage is incomplete. Family coverage is Hindu marriage/succession; civil coverage includes limitation rather than the full CPC; tax coverage is a transition FAQ rather than the full tax statutes. State/UT tenancy and employment collections are absent. Mixed state-amendment passages have conservative unknown scope.

This is a historical acquisition snapshot, not a guarantee of current law. Act/rule commencement and version applicability metadata are unknown. As-of-date research excludes those versions rather than treating website publication dates as commencement. Two other child-labour PDFs inspected were image-only and were not counted as parsed/indexed.

**Full selected source documents are included in `data/bundled/documents`.** Statutory texts accompany the original guides under the recorded reproduction basis; source notices remain intact. Thirteen Act collections also include compact, checksum-verified section records and acquisition response hashes. Original HTML/API payloads, private data, databases and model weights are excluded.

The documented setup/run scripts load the sources automatically. For direct/manual startup or a different data directory, load them explicitly without a network connection, or use **Load project documents offline** in Workspace settings:

```powershell
.\.venv\Scripts\python.exe -m vidhaan.cli load-bundled
.\.venv\Scripts\python.exe -m vidhaan.cli search 'What passage covers wholesome drinking water in plantations?'
```

```bash
.venv/bin/python -m vidhaan.cli load-bundled
.venv/bin/python -m vidhaan.cli search 'What passage covers wholesome drinking water in plantations?'
```

Inspect title, exact quote, source URL, version/checksum and review status. PDFs retain physical pages. Thirteen English Act documents are reproducible renderings of the department's public section collection: authoritative section/schedule labels and original JSON response checksums are retained; no PDF pagination is invented. The downloader checks actual source body titles, complete pagination and Act membership. Missing, partial or changed collections are reported; a checksum mismatch requires inspected version updates. No silent synthetic substitute is imported.

Repeated offline loads preserve user review, excluded versions and newer source versions. The previously acquired Bonded Labour original is included, so its earlier HTTP 403 does not block first use. `python -m vidhaan.cli acquire` remains an explicit online command for the 23-source acquisition manifest; byte changes and network failures are reported. No source download runs automatically.

For an immediate offline engineering demo, explicitly load the invented fixture:

```bash
# Windows: replace .venv/bin/python with .\.venv\Scripts\python.exe
.venv/bin/python -m vidhaan.cli demo
.venv/bin/python -m vidhaan.cli search 'written consent' --namespace synthetic --review-mode synthetic
```

Synthetic fixtures are isolated from Demo research and Reviewed research. They demonstrate the pipeline, not Indian law.

## Research modes

- **Evidence-only:** real BM25 rankings and exact extracts. `supported` means matching extracts were found; it does not certify an answer or legal applicability.
- **Demo research:** permits unreviewed official material with visible unknowns. Enable local Ollama only after installing a candidate model.
- **Reviewed research:** only reviewed versions with a recorded verification date; importing/indexing never confers review.
- **Synthetic fixture:** explicit, labelled software demonstration; excluded from legal-source search.
- **Private session:** local uploaded PDF/TXT/Markdown facts; BM25 only. The paired inspection action returns both an uploaded clause and official evidence as a possible issue requiring human review.

The UI offers all eight domains, jurisdiction/state/date/version filters, original-file download, full section context, manual review, coverage, Markdown/JSON exports, evaluation results and diagnostics. Scope or corpus changes invalidate session answers. Private data and history are not packaged or stored in query logs. Use the explicit clear action; local files are not encrypted or securely erased.

## Optional models and retrieval

The base requirements do not depend on PyTorch, sentence-transformers, FAISS, TensorFlow or Ollama. Install `requirements-embeddings.txt` only when wanted. Windows/Linux use CPU PyTorch wheels; macOS uses its native distribution. `requirements-faiss.txt` is optional: vector search selects FAISS if installed, otherwise reports NumPy cosine search. No CUDA or TensorFlow package is mandatory.

```bash
.venv/bin/python -m pip install -r requirements-embeddings.txt
.venv/bin/python -m pip install -r requirements-faiss.txt  # optional; NumPy fallback otherwise
.venv/bin/python -m vidhaan.cli cache-model             # explicit BAAI/bge-small-en-v1.5 download
.venv/bin/python -m vidhaan.cli index-dense
.venv/bin/python -m vidhaan.cli search 'drinking water' --mode hybrid
```

Windows uses the corresponding `.venv\Scripts\python.exe` command. Use these requirement files for CPU installation rather than unconstrained `pip install torch`. The equivalent project extra requires the CPU index on Windows/Linux. Embeddings run on CPU in both profiles for portability. Model initialization is cached; SQLite and vector snapshots persist. Indexing is separate from chat and never runs automatically on a page change or research request. Actual token counts, including special tokens, are checked before embedding; complete legal text is preserved in linked section parents.

Install free Ollama separately from its official distribution; choose a candidate:

```text
ollama pull qwen3:4b
ollama list
```

`lenovo_cpu`: qwen3:4b, 4,096 total context, thinking disabled, one generation, short output. `mac_m5`: qwen3.5:9b candidate, 8,192 context; the smaller option remains configurable. Tags must be available in your installed Ollama; no tag is promised to exist or be legally superior. No LLM weights are downloaded into this cloud or bundled.

Copy `.env.example` to `.env` for local settings. Model, context/output/evidence/history budgets, top-k, timeouts, vector backend and optional reranking are configurable using `VIDHAAN_*` fields in `config.py`. Invalid total-context budgets are rejected. CPU reranking is disabled by default and needs an explicit cached small cross-encoder; see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Interface development

Launching needs Python only. Editing the interface needs Node 22.12+ (Node 24 is tested). From `frontend`, run `npm ci`, `npm run dev` alongside the Python server, and `npm run build` before packaging. `npm test` runs Chromium workflows in an isolated corpus. See [docs/WEB_INTERFACE.md](docs/WEB_INTERFACE.md) for browser installation, session boundaries, accessibility and API checks.

## Code and commands

```text
app.py                   local FastAPI server entry
frontend/                React source, CSS, build lockfile and browser tests
vidhaan/web/             compiled interface assets included for Python-only launch
vidhaan/                 config, schemas, registry, ingestion, sources, chunking,
                         indexing, retrieval, providers, answers, citations, evaluation, UI
data/{raw,processed,indexes,registry}/   generated local data, separate from source
tests/fixtures/          clearly synthetic non-private material
evaluations/             benchmark schemas and measured reports
scripts/                 portable setup/run, benchmark authoring and safe ZIP build
configs/ docs/           profiles, design and walkthrough
```

```bash
.venv/bin/python -m vidhaan.cli --help
.venv/bin/python -m vidhaan.cli coverage
.venv/bin/python -m vidhaan.cli load-bundled
.venv/bin/python -m vidhaan.cli diagnostics
.venv/bin/python -m scripts.validate_corpus
.venv/bin/python scripts/document_corpus.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_benchmark.py
.venv/bin/python -m vidhaan.cli evaluate
.venv/bin/python scripts/package_project.py
```

For tests install the dev profile first. The full acquired-corpus benchmark has 61 cases; the included 21-source corpus has 54 (15 development / 39 held-out), with results in `evaluations/bundled`. Rebuild labels after source/chunk/metadata changes; the builder omits only the two known download-only FAQs when absent. Labels use passage anchors independently of rankings and require human inspection. Corpus mismatches fail evaluation. `validate_corpus` verifies the inspected unreviewed snapshot and its eight domain searches; update review/date expectations after real review.

See [SETUP_WINDOWS.md](SETUP_WINDOWS.md), [SETUP_MAC.md](SETUP_MAC.md), [DATA_SOURCES.md](DATA_SOURCES.md), [EVALUATION.md](EVALUATION.md), [LIMITATIONS.md](LIMITATIONS.md), [BUILD_STATUS.md](BUILD_STATUS.md), and the [university demo](docs/DEMO_WALKTHROUGH.md).
