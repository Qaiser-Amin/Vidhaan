import importlib.util
import platform
import json
from .providers import Ollama


def diagnose(settings,registry):
    provider=Ollama(settings)
    try:
        server=provider.status()
    finally:
        provider.close()
    snapshots=[]
    for path in (settings.data_dir/'indexes').glob('dense-*.json'):
        try:
            meta=json.loads(path.read_text())
            snapshots.append({'namespace':meta['namespace'],'identity':meta['identity'],
                'matches_corpus':meta['corpus_signature']==registry.signature(meta['namespace']),
                'chunks':len(meta['chunk_ids'])})
        except (OSError,ValueError,KeyError):snapshots.append({'file':path.name,'status':'corrupt'})
    return {'python':platform.python_version(),'platform':platform.platform(),'profile':settings.profile,
        'ollama':server,'selected_model':settings.model,'embedding_model':settings.embedding_model,
        'embedding_status':'not loaded; index-dense validates cached weights',
        'optional_dependencies':{m:importlib.util.find_spec(m) is not None for m in ['torch','sentence_transformers','faiss']},
        'dense_snapshots':snapshots,'corpus_signature':registry.signature('official'),
        'context_budget':{k:getattr(settings,k) for k in ['context_tokens','output_tokens','evidence_tokens','history_tokens']}}
