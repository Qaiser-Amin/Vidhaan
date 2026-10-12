from collections import Counter
import json
from vidhaan.config import Settings
from vidhaan.ingestion import ingest_bytes
from vidhaan.lexical import build_all, ensure_domain, token_documents
from vidhaan.models import Domain, Filters, Source
from vidhaan.retrieval import Retriever, bm25_rank
from vidhaan.tokenization import tokenize


def test_domain_indexes_match_baseline_and_skip_private(registry):
    for domain, text in [(Domain.contracts, 'SYNTHETIC written consent is required unless waived.'),
                         (Domain.family, 'SYNTHETIC family beneficiary consent is required.')]:
        ingest_bytes(registry, text.encode(), domain.name+'.txt', Source(document_id=domain.name, title='SYNTHETIC '+domain.name, domain=domain))
    ingest_bytes(registry, b'PRIVATE fixture excluded from public indexes and source counts.', 'private.txt',
                 Source(document_id='private', title='PRIVATE fixture', domain=Domain.contracts, namespace='private:test'))
    reports=build_all(registry);assert len(reports)==8
    report=next(r for r in reports if r['domain']==Domain.contracts.value);assert report['sources']==1
    data=json.loads((registry.data_dir/'indexes'/report['file']).read_text())
    mapped=token_documents(data);chunks=registry.chunks(namespace='official')
    selected=[c for c in chunks if c.domain==Domain.contracts]
    assert Counter(mapped[selected[0].chunk_id])==Counter(tokenize(selected[0].text))
    assert bm25_rank('written consent',selected,5,token_map=mapped)==bm25_rank('written consent',selected,5)
    assert 'private:test' not in json.dumps(data) and 'PRIVATE' not in json.dumps(data)


def test_tampering_and_source_changes_rebuild_indexes(registry):
    result=ingest_bytes(registry,b'SYNTHETIC written consent for this test agreement.', 'law.txt',
                        Source(document_id='law',title='SYNTHETIC law',domain=Domain.contracts))
    tokens,old=ensure_domain(registry,Domain.contracts);path=registry.data_dir/'indexes'/old['file']
    data=json.loads(path.read_text());data['postings']['forged']=[[0,1]];data['document_lengths'][0]+=1;path.write_text(json.dumps(data))
    tokens,new=ensure_domain(registry,Domain.contracts)
    assert 'forged' not in next(iter(tokens.values()))
    assert new['sha256']==old['sha256']
    registry.deactivate(result.version_id)
    tokens,new=ensure_domain(registry,Domain.contracts)
    assert not tokens and new['signature']!=old['signature']


def test_related_domain_indexes_only_include_scoped_passages(registry):
    source=Source(document_id='property',title='SYNTHETIC property authority',domain=Domain.property)
    result=ingest_bytes(registry,b'Section 1. SYNTHETIC family gifts and written consent.\n\nSection 2. SYNTHETIC unrelated warehouse regulation.', 'source.txt',source)
    chunks=registry.chunks(result.version_id);chosen=next(c for c in chunks if 'family gifts' in c.text)
    stored=registry.source(result.version_id)
    stored.related_domain_passages={Domain.family:['chunk:'+chosen.chunk_id]}
    with registry.connection() as db:
        db.execute('UPDATE versions SET metadata=? WHERE version_id=?',(stored.model_dump_json(),result.version_id));registry.bump(db)
    tokens,report=ensure_domain(registry,Domain.family)
    assert list(tokens)==[chosen.chunk_id] and report['sources']==1
    family=next(r for r in registry.coverage() if r['domain']==Domain.family.value)
    assert family['sources']==1 and family['primary_sources']==0 and family['related_sources']==1
    retriever=Retriever(registry,Settings(data_dir=registry.data_dir))
    assert retriever.search('family gifts',Filters(domain=Domain.family))
    assert not retriever.search('warehouse regulation',Filters(domain=Domain.family))


def test_title_typography_does_not_change_identity():
    from vidhaan.official_sections import title_in_body
    assert title_in_body("Employees' Compensation Act, 1923", '[EMPLOYEES’] COMPENSATION ACT, 1923')
    assert title_in_body('Recovery of Debts and Bankruptcy Act, 1993','Recovery of Debts [and Bankruptcy] Act, 1993')
    assert not title_in_body('Consumer Protection Act, 2019','Consumer Protection Act, 1986')
