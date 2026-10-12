from datetime import date
import pytest
from vidhaan.models import Filters,Domain
from vidhaan.retrieval import Retriever,tokenize,rrf
from vidhaan.answering import ResearchService
from vidhaan.indexing import IndexUnavailable


class MockDense:
    """Artificial rankings; validates pre-ranking scope, not real embedding accuracy."""
    backend='mock-test-only'
    def __init__(self,*args):pass
    def rank(self,question,eligible,limit):return [(c,0.5) for c in eligible][:limit]


@pytest.mark.parametrize('mode',['bm25','dense','hybrid'])
@pytest.mark.parametrize('scope,expected',[
    ({}, {'central','kashmir','delhi','unknown'}),
    ({'state':'Jammu and Kashmir'}, {'central','kashmir'}),
    ({'jurisdiction':'central'}, {'central'}),
    ({'as_of':date(2024,1,1)}, {'central','kashmir'}),
    ({'as_of':date(2028,1,1)}, {'central','delhi'}),
])
def test_consistent_filtering_before_ranking(registry,settings,add_document,mode,scope,expected):
    add_document('SYNTHETIC consent central evidence',document_id='central',effective_date='2020-01-01')
    add_document('SYNTHETIC consent Kashmir evidence',document_id='kashmir',jurisdiction='state',states=['Jammu and Kashmir'],effective_date='2020-01-01',effective_until='2025-01-01')
    add_document('SYNTHETIC consent Delhi evidence',document_id='delhi',jurisdiction='state',states=['Delhi'],effective_date='2026-01-01')
    add_document('SYNTHETIC consent unknown evidence',document_id='unknown',jurisdiction='unknown',publication_date='2010-01-01')
    hits=Retriever(registry,settings,MockDense).search('consent',Filters(**scope),mode,limit=20)
    assert {h.chunk.document_id for h in hits}==expected


@pytest.mark.parametrize('mode',['bm25','dense','hybrid'])
def test_supersession_delete_and_review_modes(registry,settings,add_document,mode):
    old=add_document();new=add_document('SYNTHETIC written consent new version',supersedes=old.version_id)
    retriever=Retriever(registry,settings,MockDense)
    assert {h.chunk.version_id for h in retriever.search('consent',Filters(),mode)}=={new.version_id}
    assert not retriever.search('consent',Filters(review_mode='reviewed'),mode)
    registry.review(new.version_id,'reviewed','Synthetic test review','2026-01-01')
    assert retriever.search('consent',Filters(review_mode='reviewed'),mode)
    registry.delete(new.version_id)
    assert not retriever.search('consent',Filters(),mode)


def test_namespace_boundaries(registry,settings,add_document):
    add_document(namespace='synthetic');add_document('SYNTHETIC private consent fixture',namespace='private:session-a')
    retriever=Retriever(registry,settings)
    assert not retriever.search('consent')
    assert retriever.search('consent',Filters(namespace='synthetic',review_mode='synthetic'))
    assert not retriever.search('consent',Filters(namespace='private:session-b',review_mode='private'))
    assert retriever.search('consent',Filters(namespace='private:session-a',review_mode='private'))
    registry.clear_private('private:session-a');assert not registry.versions('private:session-a')


def test_section_numbers_preserved():
    assert tokenize('Section 26 and section 2A, I.P.C. 1948')==['26','2a','i.p.c','1948']


def test_evidence_gap_and_clarification(registry,settings,add_document):
    service=ResearchService(registry,settings)
    assert service.answer('consent').status=='insufficient evidence'
    assert service.answer('Can my employer dismiss me?').status=='needs clarification'
    assert service.answer('What tenancy rules apply?',Filters(domain=Domain.property)).status=='needs clarification'
    add_document()
    assert service.answer('consent',Filters(as_of=date(2026,1,1))).status=='insufficient evidence'


def test_cache_invalidation(registry,settings,add_document):
    result=add_document();service=ResearchService(registry,settings)
    assert service.answer('consent').evidence
    registry.deactivate(result.version_id)
    assert service.answer('consent').status=='insufficient evidence'


def test_dense_snapshot_change_invalidates_answer_cache(registry,settings,add_document):
    import hashlib
    add_document();service=ResearchService(registry,settings)
    service.answer('consent');assert len(service.cache)==1
    name='dense-'+hashlib.sha256(b'official').hexdigest()[:12]+'.json'
    (registry.data_dir/'indexes'/name).write_text('{"test_snapshot":"artificial index revision"}')
    service.answer('consent');assert len(service.cache)==2


def test_version_conflict(registry,settings,add_document):
    add_document('1. Fictional rule\nSYNTHETIC consent is required for classroom use.')
    add_document('1. Fictional rule\nSYNTHETIC consent is not required for classroom use.')
    answer=ResearchService(registry,settings).answer('consent',Filters(include_superseded=True))
    assert answer.status=='conflict'


def test_hybrid_fallback_is_explicit(registry,settings,add_document):
    add_document()
    def missing(*args):raise IndexUnavailable('test embeddings missing')
    retriever=Retriever(registry,settings,missing)
    assert retriever.search('consent',mode='hybrid')
    assert retriever.last_diagnostics['warnings'] and 'unavailable' in retriever.last_diagnostics['mode']
    with pytest.raises(IndexUnavailable):retriever.search('consent',mode='dense')


def test_rrf_dedup(registry,add_document):
    add_document();chunk=registry.chunks()[0]
    merged=rrf({'bm25':[(chunk,2)],'dense':[(chunk,.3)]})
    assert len(merged)==1 and merged[0][2]=={'bm25':1,'dense':1}


@pytest.mark.parametrize('mode',['bm25','dense','hybrid'])
def test_mixed_state_amendment_not_central_evidence(registry,settings,add_document,mode):
    add_document('1. Fictional consent\nSYNTHETIC consent. STATE AMENDMENT\nAssam\nA fictional exception.',instrument_type='Act')
    retriever=Retriever(registry,settings,MockDense)
    assert retriever.search('consent',Filters(),mode)
    assert not retriever.search('consent',Filters(jurisdiction='central'),mode)
