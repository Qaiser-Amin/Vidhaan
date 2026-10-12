import json
import httpx
import pytest
from vidhaan.sources import download_manifest


def manifest(tmp_path,url):
    path=tmp_path/'manifest.json'
    path.write_text(json.dumps({'allowed_hosts':['official.example'], 'sources':[{'url':url,'filename':'fixture.txt',
        'title_check':'synthetic title', 'metadata':{'document_id':'download','title':'Synthetic title','domain':'Labour and employment'}}]}))
    return path


@pytest.mark.parametrize('scenario',['success','off_host_redirect','html_instead','title_mismatch','oversized','timeout'])
def test_controlled_acquisition(registry,tmp_path,scenario):
    def handler(request):
        if scenario=='off_host_redirect':return httpx.Response(302,headers={'location':'https://not-allowed.example/file'})
        if scenario=='timeout':raise httpx.ReadTimeout('test',request=request)
        if scenario=='oversized':return httpx.Response(200,headers={'content-length':'99999999'})
        if scenario=='html_instead':return httpx.Response(200,text='<html>access denied</html>')
        if scenario=='title_mismatch':return httpx.Response(200,text='wrong title and synthetic content')
        return httpx.Response(200,text='Synthetic title\nSYNTHETIC test acquisition content with qualifiers.')
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results=download_manifest(registry,manifest(tmp_path,'https://official.example/test.txt'),client)
    assert results[0]['status']==('imported' if scenario=='success' else 'failed')
    if scenario=='success':
        assert registry.versions()[0]['source'].review_status=='unreviewed'


def test_non_https_and_unlisted_hosts_rejected(registry,tmp_path):
    for url in ['http://official.example/test','https://evil.example/test']:
        with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,text='Synthetic title test content'))) as client:
            assert download_manifest(registry,manifest(tmp_path,url),client)[0]['status']=='failed'
