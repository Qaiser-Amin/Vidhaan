"""Measured retrieval metrics, distinct from human legal/semantic judgments."""
from pathlib import Path
import csv
import json
import platform
import statistics
import time
from pydantic import BaseModel, Field
from .models import Filters
from .indexing import IndexUnavailable


class BenchmarkCase(BaseModel):
    id: str
    split: str
    question: str
    expected_evidence_ids: list[str] = Field(default_factory=list)
    expected_document_ids: list[str] = Field(default_factory=list)
    scope: Filters = Field(default_factory=Filters)
    expected_behavior: str = 'supported'
    provenance: str
    human_review: str = 'pending'
    notes: str | None = None


def evaluate(registry, settings, cases_path: Path, output: Path, modes=('bm25','dense','hybrid'), split='heldout'):
    from .retrieval import Retriever
    from .answering import clarification
    raw = json.loads(Path(cases_path).read_text())
    cases = [BenchmarkCase(**c) for c in raw['cases'] if c['split'] == split]
    if raw.get('corpus_signature') and raw['corpus_signature'] != registry.signature('official'):
        raise ValueError('Benchmark corpus signature differs. Rebuild and inspect source labels before evaluating changed material.')
    if not cases:
        raise ValueError('No benchmark cases in the selected split; a zero-case run is invalid')
    rows = []
    for mode in modes:
        retriever = Retriever(registry, settings)
        availability_error = None
        if mode in ('dense','hybrid'):
            from .indexing import DenseIndex
            try:
                DenseIndex(registry,settings,'official')
            except IndexUnavailable as exc:
                availability_error = str(exc)
        for case in cases:
            start = time.perf_counter()
            row = {'case_id':case.id,'split':case.split,'mode':mode,'status':'run',
                   'recall_at_k':None,'mrr':None,'behavior_correct':None,'human_legal_support':'pending'}
            if availability_error:
                row.update(status='not_run',reason=availability_error,latency_seconds=None)
                rows.append(row)
                continue
            try:
                clarify = clarification(case.question, case.scope)
                hits = [] if clarify else retriever.search(case.question,case.scope,mode)
                expected = set(case.expected_evidence_ids)
                found = [h.chunk.chunk_id for h in hits]
                if expected:
                    row['recall_at_k'] = len(expected & set(found)) / len(expected)
                    row['mrr'] = next((1/i for i,cid in enumerate(found,1) if cid in expected),0.0)
                behavior = 'needs clarification' if clarify else 'supported' if hits else 'insufficient evidence'
                row['behavior_correct'] = behavior == case.expected_behavior
                row['evidence_ids'] = found
                row['actual_behavior'] = behavior
                if retriever.last_diagnostics.get('warnings') and mode == 'hybrid':
                    row['status'] = 'fallback_bm25'
            except IndexUnavailable as exc:
                row.update(status='not_run',reason=str(exc))
            row['latency_seconds'] = time.perf_counter()-start
            rows.append(row)
    summaries = {}
    for mode in modes:
        ran = [r for r in rows if r['mode']==mode and r['status']=='run']
        measured = [r for r in ran if r['recall_at_k'] is not None]
        summaries[mode] = {'run_cases':len(ran), 'evidence_scored_cases':len(measured),
                          'recall_at_k':statistics.mean(r['recall_at_k'] for r in measured) if measured else None,
                          'mrr':statistics.mean(r['mrr'] for r in measured) if measured else None,
                          'median_latency_seconds':statistics.median(r['latency_seconds'] for r in ran) if ran else None,
                          'behavior_accuracy':statistics.mean(r['behavior_correct'] for r in ran) if ran else None}
    try:
        import psutil
        memory = psutil.Process().memory_info().rss
    except ImportError:
        memory = None
    report = {'schema_version':1,'corpus_signature':registry.signature('official'),'created_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'environment':{'os':platform.platform(),'python':platform.python_version(),'processor':platform.processor(),
                       'rss_bytes':memory,'target_laptop':False},
        'split':split,'case_count':len(cases),'k':settings.top_k,'summaries':summaries,'rows':rows,
        'human_legal_correctness':'pending','semantic_citation_support':'pending',
        'real_ollama_answers':'not_run','threshold':{'min_lexical_terms':settings.min_lexical_terms,
        'note':'Engineering lexical gate; not a calibrated probability or validated legal sufficiency threshold.'}}
    output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (output/'results.csv').open('w',newline='',encoding='utf-8') as fp:
        keys = ['case_id','split','mode','status','recall_at_k','mrr','behavior_correct','latency_seconds','human_legal_support']
        writer=csv.DictWriter(fp,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    return report
