import hashlib
import io
import pytest
from reportlab.pdfgen import canvas
from vidhaan.ingestion import ingest_bytes, safe_filename
from vidhaan.models import Source, Domain
from vidhaan.registry import Registry


def pdf_bytes(pages):
    buffer=io.BytesIO();pdf=canvas.Canvas(buffer)
    for lines in pages:
        y=790
        for line in lines:
            pdf.drawString(35,y,line);y-=16
        pdf.showPage()
    pdf.save();return buffer.getvalue()


def test_idempotent_and_raw_preserved(registry,add_document):
    first=add_document();second=add_document()
    assert first.created and not second.created and first.version_id==second.version_id
    assert len(registry.versions())==1
    version=registry.versions()[0]
    assert hashlib.sha256((registry.data_dir/version['raw_path']).read_bytes()).hexdigest()==version['checksum']


def test_checksum_duplicate_even_renamed(registry,add_document):
    first=add_document();second=add_document(document_id='renamed')
    assert second.version_id==first.version_id and not second.created


def test_versions_preserve_old_citations(registry,add_document):
    first=add_document();old=registry.chunks(first.version_id)[0]
    newer=add_document('1. Fictional consent\nSYNTHETIC consent has a changed qualification.\n',supersedes=first.version_id)
    assert len(registry.versions())==2 and registry.chunk(old.chunk_id).text==old.text
    assert not next(v for v in registry.versions() if v['version_id']==first.version_id)['active']
    assert newer.version_id!=first.version_id


def test_pdf_pages_and_qualifiers(registry):
    content=pdf_bytes([['SYNTHETIC TEST PDF','1. Fictional rule. - Consent is retained, provided that'],['the written exception remains available.']])
    result=ingest_bytes(registry,content,'test.pdf',Source(document_id='pdf',title='Synthetic test PDF',domain=Domain.employment,instrument_type='Act'))
    chunks=registry.chunks(result.version_id)
    cross=[c for c in chunks if 'provided that' in c.text][0]
    assert cross.page_start==1 and cross.page_end==2
    assert cross.printed_page is None and 'exception' in cross.text
    assert registry.chunk(cross.parent_id).locator.startswith('Section 1')


def test_scanned_pdf_is_not_indexed(registry):
    result=ingest_bytes(registry,pdf_bytes([[]]),'scan.pdf',Source(document_id='scan',title='Blank synthetic PDF',domain=Domain.employment))
    assert result.chunks==0 and result.warnings
    assert registry.source(result.version_id).parsing_status=='needs_ocr'
    assert registry.source(result.version_id).extraction_warnings
    assert registry.coverage()[0]['indexed']==0


@pytest.mark.parametrize('content,name',[ (b'<html>error</html>','wrong.pdf'), (b'\x00binary file here','bad.txt'), (b'\xff\xfe','bad.md'), (b'anything here','bad.exe'), (b'','empty.txt') ])
def test_invalid_files(registry,content,name):
    with pytest.raises(ValueError):ingest_bytes(registry,content,name,Source(document_id='bad',title='Bad test file',domain=Domain.employment))


@pytest.mark.parametrize('name',['../../etc/passwd.txt','..\\..\\secret.txt','/root/contract.md'])
def test_path_traversal_is_sanitized(name):
    assert '/' not in safe_filename(name) and '\\' not in safe_filename(name)


def test_review_is_manual_and_audited(registry,add_document):
    result=add_document(review_status='reviewed',reviewer_notes='import must not confer review')
    assert registry.source(result.version_id).review_status=='unreviewed'
    registry.review(result.version_id,'reviewed','Fictional manual software test','2026-01-01')
    assert registry.source(result.version_id).last_verification_date.isoformat()=='2026-01-01'
    with registry.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM audit WHERE action='manual_review'").fetchone()[0]==1
    with pytest.raises(ValueError):registry.review(result.version_id,'reviewed','')


def test_reload_preserves_chunks(registry,add_document):
    add_document();ids=[c.chunk_id for c in registry.chunks()]
    other=Registry(registry.data_dir)
    assert [c.chunk_id for c in other.chunks()]==ids
