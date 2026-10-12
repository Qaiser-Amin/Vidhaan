"""Validate ZIP paths/hashes, fresh extraction, actual base UI and fixture evidence.

Selected public corpus files may be bundled; private files and model weights
are excluded. This script can use an explicitly selected base interpreter.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def extract_verified(archive_path,destination):
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip():raise ValueError('ZIP CRC check failed')
        for member in archive.infolist():
            path=Path(member.filename)
            if path.is_absolute() or '..' in path.parts or path.parts[0]!='vidhaan':
                raise ValueError('Unsafe ZIP member')
            if ((member.external_attr>>16)&0o170000)==0o120000:raise ValueError('ZIP symlink not permitted')
        archive.extractall(destination)
    root=destination/'vidhaan'
    manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
    for name,checksum in manifest.items():
        path=destination/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:raise ValueError('Source hash mismatch')
    return root


def validate(root,python):
    script='''
import json,sys,importlib.util
from fastapi.testclient import TestClient
from vidhaan.webapp import create_app
from vidhaan.config import get_settings
from vidhaan.registry import Registry
from vidhaan.models import Filters
from vidhaan.answering import ResearchService
from vidhaan.cli import main
bundled=__import__('pathlib').Path('data/bundled/manifest.json').exists()
if bundled:assert main(['load-bundled'])==0
with TestClient(create_app()) as client:
 page=client.get('/');assert page.status_code==200 and '<div id="root">' in page.text
 bootstrap=client.get('/api/bootstrap');assert bootstrap.status_code==200
 client.headers['X-Vidhaan-CSRF']=bootstrap.json()['csrf']
 result=client.post('/api/research',json={'question':'unfair trade practices','domain':'Consumer law'})
 assert result.status_code==200 and (not bundled or result.json()['evidence'])
 if bundled:
  hit=result.json()['evidence'][0]
  assert client.get('/api/chunks/'+hit['chunk']['chunk_id']).status_code==200
  assert client.get('/api/exports/'+result.json()['answer_id']).status_code==200
assert main(['demo'])==0
settings=get_settings();registry=Registry(settings.data_dir)
answer=ResearchService(registry,settings).answer('written consent',Filters(namespace='synthetic',review_mode='synthetic'))
assert answer.status=='supported' and 'SYNTHETIC' in answer.text
if bundled:
 from scripts.validate_corpus import validate as validate_real_corpus
 real=validate_real_corpus(registry,settings)
 assert real['sources']==21 and real['domain_count']==8 and real['official_child_chunks']==5786
else:
 assert not ResearchService(registry,settings).answer('written consent').evidence
 real=None
print(json.dumps({'base_web_ui':'passed','consumer_api_context_export':'passed' if bundled else 'empty corpus','synthetic_bm25':'passed','bundled_corpus':{'sources':real['sources'],'domains':real['domain_count'],'passages':real['official_child_chunks']} if real else None,
 'optional_dependencies':{m:importlib.util.find_spec(m) is not None for m in ['torch','sentence_transformers','faiss']}}))
'''
    result=subprocess.run([str(python),'-c',script],cwd=root,capture_output=True,text=True,timeout=120)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return json.loads(result.stdout.strip().splitlines()[-1])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('destination',type=Path)
    parser.add_argument('--python',type=Path);parser.add_argument('--extract-only',action='store_true');args=parser.parse_args()
    root=extract_verified(args.archive,args.destination)
    print(json.dumps({'extracted':str(root)}))
    if not args.extract_only:
        interpreter=args.python or root/'.venv'/('Scripts/python.exe' if __import__('os').name=='nt' else 'bin/python')
        print(json.dumps(validate(root,interpreter)))
