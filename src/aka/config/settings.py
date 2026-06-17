"""Typed configuration. No magic numbers live inside modules — they live in
``config/*.yaml`` and are validated here. The container is the only consumer.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    docs_dir: str = "docs"
    index_dir: str = "var/index"
    events_path: str = "var/events.jsonl"


class EmbeddingConfig(BaseModel):
    provider: str = "sentence-transformers"  # | "fake"
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    fake_dim: int = 64  # only used by the fake embedder (offline/tests)


class RetrievalConfig(BaseModel):
    top_k: int = 4
    # Soft relevance floor: if the best chunk scores below this, escalate instead
    # of generating. A weak signal, NOT calibrated confidence.
    relevance_floor: float = 0.25


class LLMConfig(BaseModel):
    provider: str = "anthropic"  # | "fake"
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024
    temperature: float = 0.0


class PolicyConfig(BaseModel):
    enabled: bool = True
    # Hard denials (regex, case-insensitive). Empty by default — KB grounding is
    # the primary scope guard; this is a thin optional safety net.
    deny_patterns: list[str] = Field(default_factory=list)


class Settings(BaseModel):
    paths: PathsConfig = PathsConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    llm: LLMConfig = LLMConfig()
    policy: PolicyConfig = PolicyConfig()
    # Topic graph: matched-topic -> related topics. Loaded from recommendation.yaml.
    recommendations: dict[str, list[str]] = Field(default_factory=dict)
    # Root the relative paths above resolve against (the project dir).
    root: str = "."

    def resolve(self, attr_path: str) -> Path:
        """Resolve a dotted path attribute (e.g. 'paths.index_dir') against root."""
        node: object = self
        for part in attr_path.split("."):
            node = getattr(node, part)
        return (Path(self.root) / str(node)).resolve()


_CONFIG_FILES = {
    "paths": "app.yaml",
    "embedding": "embedding.yaml",
    "retrieval": "retrieval.yaml",
    "llm": "llm.yaml",
    "policy": "policy.yaml",
}


def load_settings(root: str | Path = ".", config_dir: str | Path = "config") -> Settings:
    """Load and merge the per-concern YAML files into a validated Settings object.

    Missing files fall back to the defaults above, so the system runs out of the
    box and config is purely additive.
    """
    root = Path(root)
    cfg_dir = root / config_dir
    data: dict = {"root": str(root)}

    for section, filename in _CONFIG_FILES.items():
        path = cfg_dir / filename
        if path.exists():
            loaded = yaml.safe_load(path.read_text()) or {}
            data[section] = loaded

    rec_path = cfg_dir / "recommendation.yaml"
    if rec_path.exists():
        rec = yaml.safe_load(rec_path.read_text()) or {}
        data["recommendations"] = rec.get("topics", rec)

    return Settings(**data)
