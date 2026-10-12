# Build status

Author: Qaiser Amin Ganaie. Cloud build: 12 October 2026, Python 3.12.14 / Linux.

## Current domain expansion

- The offline release includes **83 unique official-host documents, 16,297 child passages, 66 reproducible Act section collections, and eight portable BM25 inverted indexes**. Each domain has 10–12 source documents: employment 12, consumer 11, contracts 10, property 10, family 10, procedure 11, corporate/tax 12 and specialist 12.
- Family has five primary Acts plus five related sources. Only explicitly selected maintenance, gifts, partition, trusts and historical marital-evidence passages enter its index. Shared sources are stored once; domain totals overlap. Every version remains unreviewed and effective dates stay unknown.
- Government source bodies, complete Act pagination/membership and original SHA-256 values were inspected. Failed, partial, scanned and translated sources are excluded. Title typography is normalized only for identity checks; quoted bodies are preserved. Historical issuing authorities remain unknown where unverified.
- Runtime SQL/coverage/index operations filter namespaces before reading chunks. Only manifest-declared official-domain postings are packaged; private material, databases and runtime indexes remain excluded. Offline loads preflight checksums, validate postings against actual chunks and preserve manual review, exclusions and newer versions.
- Current cloud suite: **115 passed, zero failures/skips**. Fresh offline validation passed all 83 document checksums/66 receipts, all eight domain searches/quotes, reviewed/date gaps and a related-family BNSS maintenance search. See `evaluations/domain_index_validation.json`.
- Current 83-source held-out BM25: Recall@5 34/41 (0.8293), MRR 0.6065, broad behavior 47/47. Dense/hybrid/generation remain unrun. No held-out tuning; legal support remains unreviewed.
- Chromium browser suite: **7 passed, zero failures/skips**, including all eight counts, the matching 83-source report, related Family/BNSS evidence, source/original downloads, private isolation, mobile layouts and physical PDF pages.
- Fresh extracted ZIP shell setup/dev installation and launch passed. Base-only suite: **114 passed, one optional FAISS skip, zero failed**; Torch, sentence-transformers and FAISS are absent. Real consumer context/export, all eight domain/quote/hash checks, new DPDP consent evidence and the matching benchmark passed. Native Windows/macOS and real model generation remain unperformed.
- Cloud startup instructions were saved with the expanded counts and index workflow; draft saving does not publish an environment.
- The following sections record earlier snapshots and their historical measurements; their 21/23-source counts do not describe this release.

## Completed implementation

- Local Python/FastAPI and React legal research app, eight domains, SQLite source/version registry, manual review audit, exact section parents/children, persistent BM25 and citation/quote validation.
- Optional CPU embeddings, FAISS/NumPy snapshots, hybrid retrieval, reranking and structured Ollama generation; base app works without those optional dependencies/models.
- Scope/date/version/review filters, private session documents, source viewer/downloads, research export, coverage, evaluations and diagnostics.
- Portable setup/run scripts, bounded explicit HTTPS acquisition, benchmark builder, domain-document generator, corpus validation and safe source ZIP builder.

## Expanded official-host corpus

- Preserved the original five Ministry of Labour sources and acquired **18 new sources successfully, zero acquisition failures** in the expansion run.
- **23 distinct sources and versions, all parsed/indexed; 5,819 official child passages; zero reviewed.** Four isolated synthetic fixture passages are excluded from the official count.
- Domain counts: employment 5; consumer 1; contracts 3; property 2; family 2; criminal/civil procedure 4; corporate/tax 3; specialist 3.
- Sources: Ministry of Labour, Ministry of Home Affairs and Income Tax Department. Three new criminal-law Acts are readable English Gazette PDFs. Thirteen Act documents are English department section collections comprising 1,550 returned section/schedule records. RTI PDF and tax-transition FAQ complete the expansion.
- API acquisition validates complete pagination, source body titles and Act membership, rejects duplicate/missing records, retains original JSON hashes and authoritative locators, and executes no source scripts. Plain-text renderings have no invented PDF pagination. Rechunking verifies original/derived integrity.
- Historical issuing authority remains unknown for the three pre-independence Acts; modern Parliament is not asserted as their original issuer. Publication date is verified for the three Gazette Acts; all version effective dates remain unknown.
- Eight source-linked research documents are in `docs/domains/`; each lists actual documents, scope, gaps, example searches and version/checksum provenance. See DATA_SOURCES.md.

## Validation evidence

- Current cloud suite before bundling: **92 passed, zero failed/skipped** (`evaluations/pytest.xml`). Includes acquisition pagination/scope/title/integrity failures and receipt-preserving rechunking; native FAISS checks use artificial vectors.
- `python -m scripts.validate_corpus`: all 23 document hashes and 13 original-response/derived collections passed; all eight domain searches retrieved expected sources and exact quotations. Reviewed-mode and unknown-date gaps passed.
- Historical Streamlit consumer section-collection and BNSS PDF searches passed; section-source cards and physical-page evidence render. Live existing service health passed. See `evaluations/ui_smoke.json`.
- Expanded benchmark: **61 cases, 17 development / 44 held-out**. BM25 Recall@5 **0.8421 (32/38)**, MRR **0.7083**, held-out broad behavior 44/44. Six labelled passages are missed; the development irrelevant-query false positive remains. Human semantic/legal review pending. Historical gate tuning is separate.
- Documented property CLI search with explicit central jurisdiction passed. ZIP selection excludes raw originals, API snapshots, SQLite, private files, secrets, environments and models.
- Prior portable shell setup/dev installation, dependency checks and fresh base-only setup passed. Expanded export validation is recorded separately after packaging.

## External and legal limits

- India Code backend responds, but investigated public searches returned zero records. Several judicial/government hosts returned proxy denials. Legislative Department alternatives inspected were scanned/translations and excluded from English coverage; no OCR or access-control bypass was used.
- Every domain is represented, with incomplete coverage. State tenancy/employment collections, other personal laws, the full CPC, full tax statutes, comprehensive current notifications/rules and case law remain gaps. No current-law or legally reviewed corpus is claimed.
- Final project corpus: 21 sources across all eight domains, 5,786 official passages. Statutory texts accompany original guides under the recorded section 52 reproduction basis; the tax FAQ has department reuse terms. Notices remain intact; no blanket publisher/database licence is asserted. Two Labour FAQs require permission and stay download-only. Original HTML/API payloads remain outside the archive; compact records and response hashes are included.
- The previously acquired Bonded Labour PDF returned HTTP 403 on an earlier repeat; its genuine cached original remains intact. Future URL/checksum changes are reported and require inspection.
- Real BGE weights remain blocked at `us.aws.cdn.hf.co`. No real dense/hybrid/reranker benchmark, Ollama/model run or generated-answer quality/throughput measurement. Optional package installation does not establish model readiness.
- Windows/Lenovo, native macOS/M5/Metal, PowerShell execution and laptop speed/memory are unperformed. Cloud timing does not predict laptop performance.

## Environment and packaging

- Reusable install/start instructions and required source/model network domains are saved in the cloud configuration draft. Saving does not apply runtime changes or publish a reusable snapshot; review/save and publish in environment settings when wanted.
- Cloud/UI validation finished with local source changes. GitHub source publication is recorded separately in repository commit history; uploading source does not deploy a web app.
- Fresh expanded export: ZIP CRC/hash manifest and lightweight UI/synthetic evidence passed with torch, SentenceTransformers and FAISS absent. Tests: **91 passed, 1 optional FAISS skip, zero failed**. The previously verified base-only interpreter was reused against a separate fresh source extraction.
- Restored all 23 genuine documents offline into a separate test registry, including verified API receipts; all eight domain workflows and integrity/quote/review/date checks passed. Test originals were never added to the ZIP. See `evaluations/expansion_export_validation.json`.
- The earlier guides/source-only export is historical. The final project includes the 21-source offline corpus, checksum-verified loading, accompanying guides and scoped reproduction records. Fresh-export tests and source searches are recorded in `evaluations/bundle_validation.json`.

## Offline corpus integration

- `load-bundled` preflights every declared file and accompanying guide, imports only official unreviewed sources, retains exact section locators and preserves manual review/exclusion/newer versions on repeats.
- Setup/run scripts load the bundled corpus locally; the UI also provides an explicit offline-load action. No network call or model download is used by this loader.
- Loader tests cover path traversal, symlink escapes, altered documents/receipts, private namespaces, missing reuse records/guides, duplicate imports and user changes. Undeclared files are excluded from packaging.

- Final corpus integration suite: **105 passed, zero failures/skips** in the prepared cloud. Fresh base-only export: **104 passed, one optional FAISS skip, zero failed**. Its included 21 documents were loaded from archive contents alone; all eight domain, checksum, exact-quote and date/review-gap checks passed. The measured 21-source corpus has 54 benchmark cases, separate from the retained full 23-source cloud collection.
- Updated shell setup executed in a fresh extracted project and created its own base/dev environment; pip check, automatic local corpus loading and genuine consumer evidence passed. Optional model packages remained absent.
- The fresh extracted run script loaded the included corpus without source network access and started a healthy historical Streamlit service (superseded by the custom web interface). Health/root checks passed; only this test service was stopped afterward. Final ZIP excludes environments, runtime databases/private data and original API payloads.

## Custom web interface (prior 21-source release)

- Replaced Streamlit with a custom React + FastAPI workspace. Includes self-hosted serif/sans typography, responsive layouts, domain cards, staggered entrances, hover/loading feedback, and animated source/evidence drawers. Reduced-motion preferences, labelled controls, keyboard submission, focus trapping and Escape handling are implemented.
- Retains genuine retrieval, exact quotation/context, physical PDF pagination and department section links, original downloads, Markdown/JSON exports, all scope filters, private-clause inspection, audited manual review/exclusion, live coverage, measured evaluation and diagnostics. No synthetic content becomes official evidence.
- The compiled interface ships with the ZIP; users run the Python setup/launch scripts without Node. Frontend source and pinned npm lockfile are included for development. Streamlit is absent from runtime imports and requirements. Source notices and third-party font/icon licences remain included.
- Opaque browser sessions authorize private downloads, passages and exports. Mutations validate CSRF tokens and same-origin requests; request bodies and file uploads are bounded. Questions are POST bodies, access logging is disabled, and no browser history is persisted to localStorage. Session expiry does not erase retained files; explicit clearing remains available.
- Current cloud suite: **108 passed, zero failed/skipped**. Browser suite: **6 passed, zero failed/skipped**, using real bundled documents. Widths 360, 390, 600, 768, 1024 and 1440 pixels showed no horizontal overflow.
- Fresh extracted setup/dev installation: **107 passed, one optional FAISS skip, zero failed**. No Streamlit, Torch, sentence-transformers or FAISS is required there. Actual launch scripts, consumer API/context/export and all eight domain/quote/hash/date/review-gap checks passed with 21 documents and 5,786 passages.
- The final extracted interface also passed a real Chromium PDF evidence/original-download workflow, displayed physical page 9 and unknown printed pagination, and requested zero external interface resources. See evaluations/web_validation.json.
- Build/install sequencing was corrected after a concurrent rebuild temporarily removed generated assets during package discovery. Namespace package discovery is disabled; the sequential setup and frontend build paths passed.
- Native Windows/macOS and real optional model generation remain unperformed. The legal corpus, review status and retrieval measurements are unchanged by the UI replacement.
