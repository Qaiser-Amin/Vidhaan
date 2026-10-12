# Custom web interface

VIDHAAN uses a React interface served by a local FastAPI application. Streamlit is no longer a dependency or entry point. The downloadable project includes the production JavaScript, CSS, icons and fonts under `vidhaan/web`, so Node is not required to run it. All interface assets are served locally; normal startup contacts no font, analytics or CDN service.

Run the usual setup and launch scripts. `python app.py` serves one local process on port 8765; `python app.py --port 8766` or `VIDHAAN_PORT` selects another port. The launcher binds to loopback, and the interface has no hosted account or paid dependency. Open the local address printed by the server in your laptop browser.

## Interface workflows

- Research workspace: question input, Ctrl/Command + Enter, eight domain shortcuts, collection selector, jurisdiction/state/date/version filters, superseded-version comparison and private-clause inspection. BM25 works without optional model packages. Dense/hybrid and Ollama need the explicitly installed models and indexes described in CONFIGURATION.md.
- Evidence reader: exact retrieved text, full section context, genuine physical PDF pages where available, department section links, original downloads, review status, dates and SHA-256 provenance. Text is rendered as text; source content cannot inject HTML or remote images.
- Source library: search titles, filter domains, switch collections, inspect extracted sections and metadata, record actual manual review, and exclude a version from active research.
- Corpus coverage: live registry counts for collected, parsed, indexed and reviewed material across all eight domains. Count bars represent version states, not legal completeness.
- Evaluation: saved measured report with an explicit corpus match/staleness label. No model metrics are invented; unrun methods remain unmeasured.
- Settings: hardware/model profile, actual local readiness diagnostics, explicit offline/online acquisition actions, isolated synthetic fixtures and private-session clearing.

Page entrances, staggered cards, button/hover feedback, evidence drawers, loading states and the small source illustration use CSS animations. Reduced-motion preferences disable motion. The layout adapts to laptop, tablet and phone widths. Readers trap focus, support Escape and restore focus on close; all fields have labels and focus indicators.

## Local session boundaries

A server-generated opaque, HttpOnly, SameSite=Strict session cookie owns the private namespace and in-memory answers. API mutations require a session-specific CSRF token and reject foreign origins. Host checks restrict the local service. Uploaded originals remain on disk until cleared; the browser cookie is not a durable login. Session expiry (12 hours of inactivity), browser session loss or server restart does not automatically erase old files or reconnect them to a new session. Use Clear before closing when appropriate. This prototype is not a public multi-user deployment.

Research questions use bounded POST bodies and are not included in URLs or access logs. Browser state and research results stay in memory, with no localStorage history. Source/review changes clear displayed answers; exported answers must still match their corpus/index signature. Each upload is one PDF/TXT/Markdown file <=25 MiB, with bounded multipart parsing. Original downloads and chunk contexts are authorized to the same private session. Private namespaces never qualify as legal authorities.

## Frontend development

Only editing the interface needs Node **22.12+ or 24+** and npm. From `frontend`:

```bash
npm ci
npm run dev       # Python server must also be running on its default port
npm run build     # emits the production assets into ../vidhaan/web
npm test          # Chromium browser workflows against an isolated test registry
```

The development proxy uses the same origin for API requests. Python changes require restarting the Python server. Rebuild before distributing changes; the production launcher deliberately requires no npm command or browser build step.

Playwright uses `/usr/bin/chromium` when present, or a `CHROMIUM_PATH` override. Otherwise install its Chromium with `npx playwright install chromium`. The browser test runner currently uses a POSIX shell launch command; Windows users can run it under WSL. Windows PowerShell launch of the production project does not require Playwright or Node.

Python API tests cover session isolation, originals, quotations/context, exports, manual review audit, input limits, CSRF/origin/host boundaries and optional-dependency-free startup. Browser tests cover genuine consumer evidence, source text/provenance/download, upload/search/clear, mobile navigation, focus/reduced motion and the matching benchmark. Measurements are cloud/Linux checks; native Windows/macOS execution and real model generation remain separately unperformed.

Third-party interface license notices are retained in [licenses/README.md](licenses/README.md). Legal source reproduction remains governed by [CORPUS_REUSE.md](CORPUS_REUSE.md).
