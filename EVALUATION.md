# Evaluation

## Current 83-document offline release

The current corpus has 83 unique documents and 16,297 child passages. Its independently defined benchmark has **62 cases: 15 development and 47 held-out**, with eight new-source passage anchors (one per domain) added before retrieval. The lexical gate remains unchanged; no settings were tuned on held-out outcomes. Related-family maintenance and scoped indexes are also checked separately in `evaluations/domain_index_validation.json`.

Measured held-out BM25: **Recall@5 0.8293 (34/41), MRR 0.6065; broad behavior 47/47; median case latency 366.54 ms** on cloud Linux/Python 3.12.14. Seven labelled passages are missed. Development Recall@5 is 10/13 (0.7692), broad behavior 14/15; the irrelevant-query false positive remains. These are passage-location and engineering measurements, not human legal correctness. Dense/hybrid/reranker and real generation remain unrun because actual weights/models are unavailable.

Current reports: `evaluations/bundled/results.json` and `evaluations/bundled/development/results.json`; benchmark: `evaluations/bundled/benchmark.json`. Their signature matches the fresh offline 83-source load. A retained cloud registry with two extra Labour FAQs has a different signature and correctly shows earlier cloud measurements as stale. The following sections preserve historical 21/23-source results.


## Earlier 23-source dataset and protocol

61 author-defined cases: 17 development (15 passage retrieval + 2 behavior/gap cases), 44 held-out (38 passage retrieval + 6 clarification/gap cases). Twenty-three official-host source versions represent all eight domains. Questions and exact passage anchors are defined independently of retrieval rankings by `scripts/build_benchmark.py`. These are passage-location labels, not certified semantic/legal judgments; human review is pending.

Development and held-out questions are disjoint. The original employment cases remain, with 21 new domain cases. The former empty consumer/corporate cases now test reviewed-source and dated-evidence gaps because those domains have material. The benchmark is author-created, shares one corpus, and is not an external legal examination.

The lexical gate remains 1. `evaluations/threshold_tuning.json` records historical tuning on the original ten employment development cases; it is explicitly marked historical. No settings were tuned on expanded held-out outcomes. This gate is not a probability or legal sufficiency score.

## Actual expanded held-out measurement

| Mode | Retrieval cases scored | Recall@5 | MRR | Median case latency |
|---|---:|---:|---:|---:|
| BM25 | 38 | 0.8421 | 0.7083 | 516.48 ms |
| Dense BGE | not run | — | — | — |
| Hybrid with real BGE | not run | — | — | — |
| Cross-encoder reranking | not run | — | — | — |

Timestamp (UTC): 2026-10-12T17:48:30.268386+00:00. Environment: Linux-6.18.44-x86_64-with-glibc2.41; Python 3.12.14. Instantaneous process RSS: 185.58 MiB, not peak or target-laptop memory. Evaluations include registry/filter/ranking overhead; timing does not measure model token throughput.

BM25 retrieved 32 of 38 annotated passages in the first five; six were missed. All 44 held-out cases returned the expected broad status. A matching-extract status does not establish that a legal question is answered. Development Recall@5: 0.8000 (12/15); broad status: 16/17. The irrelevant-query false positive persists. Inspect individual JSON/CSV rows.

Recall@k is the fraction of gold evidence IDs in the first k chunks. MRR is reciprocal rank of the first gold ID. Behavior-only cases are excluded from Recall/MRR denominators. New property questions explicitly inspect central instruments; person-specific tenancy still requires state/UT clarification.

## Engineering checks and unperformed work

The historical pre-bundle suite had 92 passing cloud tests; current UI/API validation is recorded in BUILD_STATUS.md and evaluations/web_validation.json. The real corpus validation checks 23 source-document hashes, original response integrity for 13 English section collections (1,550 records), all eight representative domain searches, exact citation/quote structure, reviewed-mode gaps and unknown-date gaps. Historical Streamlit collection/PDF searches are recorded separately; current React browser workflows use the real included corpus. None certifies legal correctness.

CPU-only PyTorch, sentence-transformers and FAISS are installed. Real BGE weights remain blocked at `us.aws.cdn.hf.co`; dense/hybrid/reranker measurements are `not_run`. Ollama/models are absent; generated-answer quality, semantic citation support, unsupported-claim rates and model throughput were not measured. Mock/provider and artificial-vector tests are engineering checks only. Windows/Lenovo and native macOS/M5/Metal measurements remain unperformed.

## Reproduction

After installing dev dependencies and explicitly acquiring the manifest sources:

```bash
.venv/bin/python -m scripts.validate_corpus
.venv/bin/python scripts/build_benchmark.py
.venv/bin/python -m vidhaan.cli evaluate --split development --output evaluations/development
.venv/bin/python -m vidhaan.cli evaluate --split heldout --output evaluations/latest
```

Windows uses `.venv\Scripts\python.exe`. A blocked original or changed checksum needs genuine local acquisition or an inspected version update. Do not force a passing score by replacing unavailable material or labels. After genuine review/date metadata changes, update the snapshot-specific gap expectations in `validate_corpus`.

The current report signature matches the expanded official corpus. Source/chunk/metadata changes invalidate it and require rebuilding and inspecting labels. The main reports describe the 23-source cloud snapshot. The final project includes a separate measured report for the 21-source offline corpus and shows it when the local signature matches. The older extracted-validation record is historical; the expanded export check is separate.

## Final project's offline corpus

The included 21 sources produce 5,786 official passages. The two permission-restricted Labour FAQs are omitted, so the corresponding seven passage cases are absent: 54 cases total, 15 development and 39 held-out. Questions/gold anchors for retained sources are unchanged, and no settings were tuned on these held-out outcomes.

Actual bundled-corpus BM25 measurement: 33 retrieval cases, Recall@5 0.8485, MRR 0.7081, broad behavior accuracy 1.0000. Timestamp: 2026-10-12T18:20:35.058540+00:00. Dense/hybrid remain not run. These are passage-location/engineering results, not legal-quality certification.

Reproduce with `python scripts/build_benchmark.py --output evaluations/bundled/benchmark.json`, then `python -m vidhaan.cli evaluate --cases evaluations/bundled/benchmark.json --output evaluations/bundled`. Setup/launch loads the included sources first. Full cloud and bundled reports are separate and must not be compared as if they have identical case populations.
