"""Artificial embeddings exercise storage/search integrity, never legal benchmark scores."""
from types import SimpleNamespace
import json
import numpy as np
import pytest
from vidhaan.indexing import build_dense,DenseIndex,IndexUnavailable
from vidhaan.models import Filters
from vidhaan.retrieval import Retriever


class MockTokenizer:
    def encode(self,text,add_special_tokens=True,truncation=False):
        assert not truncation
        return list(text.encode())+[0,0]


class MockEmbedding:
    max_seq_length=512
    tokenizer=MockTokenizer()
    def __init__(self):self.calls=0
    def __getitem__(self,index):return SimpleNamespace(auto_model=SimpleNamespace(config=SimpleNamespace(_commit_hash='test-only')))
    def get_sentence_embedding_dimension(self):return 3
    def encode(self,texts,**kwargs):
        self.calls+=len(texts)
        vectors=np.asarray([[1+str(t).count('consent'),1+str(t).count('exception'),1] for t in texts],dtype=np.float32)
        return vectors/np.linalg.norm(vectors,axis=1,keepdims=True)


def test_atomic_snapshot_reuse_and_numpy_search(registry,settings,add_document):
    settings=settings.model_copy(update={'vector_backend':'numpy'})
    add_document();model=MockEmbedding();first=build_dense(registry,settings,model=model)
    second=build_dense(registry,settings,model=model)
    assert first['new_chunks']>0 and second['new_chunks']==0 and second['reused_chunks']>0
    index=DenseIndex(registry,settings,'official',model=model)
    ranked=index.rank('consent',registry.chunks(),5)
    assert ranked and index.backend=='numpy'


def test_stale_and_corrupt_index(registry,settings,add_document):
    result=add_document();model=MockEmbedding();build_dense(registry,settings,model=model)
    registry.review(result.version_id,'reviewed','test notes','2026-01-01')
    with pytest.raises(IndexUnavailable,match='stale'):DenseIndex(registry,settings,'official',model=model)
    metadata=build_dense(registry,settings,model=model)
    path=registry.data_dir/'indexes'/metadata['vectors_file'];path.write_bytes(b'corrupt')
    with pytest.raises(IndexUnavailable,match='checksum'):DenseIndex(registry,settings,'official',model=model)


def test_model_dimension_mismatch(registry,settings,add_document):
    add_document();model=MockEmbedding();build_dense(registry,settings,model=model)
    model.get_sentence_embedding_dimension=lambda:4
    with pytest.raises(IndexUnavailable,match='identity'):DenseIndex(registry,settings,'official',model=model)


def test_tokenizer_children_are_not_truncated(registry,settings,add_document):
    result=add_document('1. Long synthetic rule\n'+('consent provided that exception remains. '*100))
    model=MockEmbedding();build_dense(registry,settings,model=model)
    children=registry.chunks(result.version_id);parents=registry.chunks(result.version_id,kind='parent')
    assert all(len(model.tokenizer.encode(c.text))<=384 for c in children)
    assert ''.join(c.text for c in children)==''.join(c.text for c in parents)


def test_private_dense_not_persisted(registry,settings,add_document):
    add_document(namespace='private:session')
    with pytest.raises(IndexUnavailable,match='private'):build_dense(registry,settings,'private:session',MockEmbedding())


def test_faiss_matches_numpy_when_installed(registry,settings,add_document):
    pytest.importorskip('faiss',reason='Optional native backend not installed in lightweight profile')
    add_document();model=MockEmbedding();build_dense(registry,settings,model=model)
    faiss=DenseIndex(registry,settings.model_copy(update={'vector_backend':'faiss'}),'official',model=model)
    numpy=DenseIndex(registry,settings.model_copy(update={'vector_backend':'numpy'}),'official',model=model)
    a=faiss.rank('consent',registry.chunks(),5);b=numpy.rank('consent',registry.chunks(),5)
    assert [c.chunk_id for c,_ in a]==[c.chunk_id for c,_ in b]
    assert np.allclose([s for _,s in a],[s for _,s in b])
