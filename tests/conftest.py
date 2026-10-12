"""All generated documents in tests are fictional engineering fixtures."""
from pathlib import Path
import pytest
from vidhaan.config import Settings
from vidhaan.registry import Registry
from vidhaan.models import Source, Domain
from vidhaan.ingestion import ingest_bytes


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path/'data').initialize()


@pytest.fixture
def registry(settings):
    return Registry(settings.data_dir)


@pytest.fixture
def add_document(registry):
    def add(text='1. Fictional consent\nSYNTHETIC test consent applies provided that a written exception is preserved.\n', **overrides):
        metadata={'document_id':'fixture','title':'SYNTHETIC engineering fixture','domain':Domain.employment,
                  'namespace':'official','jurisdiction':'central'}
        metadata.update(overrides)
        return ingest_bytes(registry,text.encode(),'fixture.txt',Source(**metadata))
    return add
