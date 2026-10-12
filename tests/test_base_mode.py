import subprocess
import sys
from vidhaan.config import ROOT


def test_startup_with_optional_imports_blocked(tmp_path):
    script='''
import importlib.abc,sys,os
class BlockHeavy(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','sentence_transformers','faiss','tensorflow'}:
            raise ImportError('Optional dependency deliberately blocked for base-mode check')
sys.meta_path.insert(0,BlockHeavy())
from vidhaan.config import get_settings
from fastapi.testclient import TestClient
from vidhaan.webapp import create_app
with TestClient(create_app()) as client:
    assert client.get('/').status_code==200
    assert client.get('/api/health').json()['assets_ready']
from vidhaan.models import Filters
from vidhaan.registry import Registry
from vidhaan.answering import ResearchService
settings=get_settings()
assert ResearchService(Registry(settings.data_dir),settings).answer('no corpus').status=='insufficient evidence'
print('base imports, UI and evidence-gap response passed with optional imports blocked')
'''
    import os
    result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=dict(os.environ,VIDHAAN_DATA_DIR=str(tmp_path/'base')),
                          capture_output=True,text=True,timeout=40)
    assert result.returncode==0,result.stdout+result.stderr
