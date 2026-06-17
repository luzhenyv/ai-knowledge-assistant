"""Shared fixtures. The whole pipeline runs offline here: the 'fake' embedder
(deterministic hashing) and 'fake' LLM — no model downloads, no API key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aka.config.settings import load_settings
from aka.ingestion.indexer import build_index
from aka.pipeline.container import build_chat_service, build_embedder, embedding_model_id
from aka.retrieval.vector_store import NumpyVectorStore

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path):
    s = load_settings(REPO_ROOT)
    s.embedding.provider = "fake"
    s.llm.provider = "fake"
    s.paths.index_dir = str(tmp_path / "index")
    s.paths.events_path = str(tmp_path / "events.jsonl")
    return s


@pytest.fixture
def built_index(settings):
    embedder = build_embedder(settings)
    store = NumpyVectorStore(settings.resolve("paths.index_dir"))
    build_index(
        docs_dir=settings.resolve("paths.docs_dir"),
        index_dir=settings.resolve("paths.index_dir"),
        embedder=embedder,
        store=store,
        embedding_model_id=embedding_model_id(settings),
        timestamp="2026-01-01T00:00:00+00:00",
    )
    return settings


@pytest.fixture
def chat_service(built_index):
    return build_chat_service(built_index)
