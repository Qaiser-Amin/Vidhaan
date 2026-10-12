from functools import lru_cache
from pathlib import Path
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    profile: str = "evidence_only"
    data_dir: Path = ROOT / "data"
    ollama_url: str = "http://127.0.0.1:11434"
    model: str | None = None
    context_tokens: int = Field(4096, ge=1024, le=65536)
    output_tokens: int = Field(384, ge=64, le=4096)
    evidence_tokens: int = Field(1800, ge=128)
    history_tokens: int = Field(300, ge=0)
    top_k: int = Field(5, ge=1, le=20)
    timeout_seconds: float = Field(90, ge=1, le=600)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_revision: str | None = None
    embedding_local_only: bool = True
    embedding_batch_size: int = Field(8, ge=1, le=64)
    vector_backend: str = "auto"
    rerank: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    max_file_bytes: int = 25 * 1024 * 1024
    min_lexical_terms: int = 1
    instruction_reserve: int = 1100

    @model_validator(mode="after")
    def budget(self):
        if self.output_tokens + self.evidence_tokens + self.history_tokens + self.instruction_reserve > self.context_tokens:
            raise ValueError("Context budget must leave room for instructions, evidence, history and output")
        return self

    def initialize(self):
        for name in ("raw", "processed", "indexes", "registry", "private"):
            (self.data_dir / name).mkdir(parents=True, exist_ok=True)
        return self


@lru_cache(maxsize=4)
def get_settings(profile: str | None = None) -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    name = profile or os.getenv("VIDHAAN_PROFILE", "evidence_only")
    profiles = json.loads((ROOT / "configs/profiles.json").read_text())
    if name not in profiles:
        raise ValueError(f"Unknown hardware profile: {name}")
    values = dict(profiles[name], profile=name)
    for field in Settings.model_fields:
        value = os.getenv(f"VIDHAAN_{field.upper()}")
        if value is not None:
            values[field] = value
    path = Path(values.get("data_dir", ROOT / "data")).expanduser()
    values["data_dir"] = path if path.is_absolute() else ROOT / path
    return Settings(**values).initialize()
