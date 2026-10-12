from vidhaan.chunking import Page,chunk_pages,split_exact
from vidhaan.models import Source,Domain


class MockTokenizer:
    """Artificial tokenizer for testing limits, never used by application models."""
    def encode(self,text,add_special_tokens=True,truncation=False):
        assert not truncation
        return list(text.encode())+([1,2] if add_special_tokens else [])


def test_exact_split_no_loss():
    text='1. Rule\n'+('Definition applies; provided that an exception is retained.\n'*70)+'Explanation: never discard this qualifier.'
    parts=list(split_exact(text,384,MockTokenizer()))
    assert ''.join(p[2] for p in parts)==text
    assert all(len(MockTokenizer().encode(p[2]))<=384 for p in parts)
    assert 'Explanation' in parts[-1][2]


def test_long_word_cannot_silently_truncate():
    text='x'*1500
    pieces=list(split_exact(text,100,MockTokenizer()))
    assert ''.join(p[2] for p in pieces)==text and len(pieces)>10


def test_stable_parents_and_children():
    source=Source(document_id='test',title='Synthetic test',domain=Domain.employment,checksum='a'*64,source_version='testversion')
    pages=[Page(1,'1. Definitions\nMeaning with proviso.\n2. Exceptions\nNothing applies without consent.')]
    one=chunk_pages(pages,source);two=chunk_pages(pages,source)
    assert [c.chunk_id for c in one]==[c.chunk_id for c in two]
    assert len([c for c in one if c.kind=='parent'])==2
    assert all(c.parent_id for c in one if c.kind=='child')


def test_editorial_notes_are_not_invented_sections():
    source=Source(document_id='notes',title='Synthetic statute',domain=Domain.employment,
                  instrument_type='Act',checksum='b'*64,source_version='noteversion')
    text='1. Fictional rule.—An exception remains.\n1. Subs. by a fictional amendment note.\n2. Fictional exception.—Nothing is lost.'
    chunks=chunk_pages([Page(1,text)],source)
    parents=[c for c in chunks if c.kind=='parent']
    assert len(parents)==2 and parents[0].locator.startswith('Section 1')
    assert 'Subs.' in parents[0].text
