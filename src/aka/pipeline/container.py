"""The ONLY place objects are constructed. Explicit constructor injection — no
global singletons, no service locator, no dynamic registry. Swapping an
implementation (embedder, vector store, LLM) is a one-line change here.
"""

from __future__ import annotations

from aka.config.settings import Settings
from aka.contracts.embedder import Embedder
from aka.contracts.eventsink import EventSink
from aka.contracts.llm import LLM
from aka.generation.generator import GroundedAnswerGenerator
from aka.guardrail.policy import PolicyGuardrail
from aka.llm.fake import FakeLLM
from aka.observability.sink import JsonlEventSink
from aka.pipeline.pipeline import ChatService, Pipeline
from aka.pipeline.stages import (
    GenerateStage,
    GroundingStage,
    GuardStage,
    RecommendStage,
    RetrievalStage,
)
from aka.recommendation.graph import StaticGraphRecommender
from aka.retrieval.embedder import HashingEmbedder, SentenceTransformerEmbedder
from aka.retrieval.retriever import VectorRetriever
from aka.retrieval.vector_store import NumpyVectorStore


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedding.provider == "fake":
        return HashingEmbedder(dim=settings.embedding.fake_dim)
    return SentenceTransformerEmbedder(model=settings.embedding.model)


def embedding_model_id(settings: Settings) -> str:
    """Identifier recorded in the manifest so a model change invalidates the index."""
    if settings.embedding.provider == "fake":
        return f"fake:{settings.embedding.fake_dim}"
    return settings.embedding.model


def build_llm(settings: Settings) -> LLM:
    if settings.llm.provider == "fake":
        return FakeLLM()
    from aka.llm.anthropic_llm import AnthropicLLM

    return AnthropicLLM(
        model=settings.llm.model,
        max_tokens=settings.llm.max_tokens,
        temperature=settings.llm.temperature,
    )


def build_event_sink(settings: Settings) -> EventSink:
    return JsonlEventSink(settings.resolve("paths.events_path"))


def build_chat_service(
    settings: Settings, *, load_index: bool = True, sink: EventSink | None = None
) -> ChatService:
    """Compose the full serving pipeline from settings.

    ``sink`` overrides the default JSONL event sink (tests pass an in-memory one).
    """
    embedder = build_embedder(settings)
    store = NumpyVectorStore(settings.resolve("paths.index_dir"))
    if load_index:
        store.load()

    retriever = VectorRetriever(embedder, store)
    generator = GroundedAnswerGenerator(build_llm(settings))
    guard = PolicyGuardrail(
        deny_patterns=settings.policy.deny_patterns, enabled=settings.policy.enabled
    )
    recommender = StaticGraphRecommender(settings.recommendations)

    pipeline = Pipeline(
        [
            GuardStage(guard),
            RetrievalStage(retriever, top_k=settings.retrieval.top_k),
            GroundingStage(relevance_floor=settings.retrieval.relevance_floor),
            GenerateStage(generator),
            RecommendStage(recommender),
        ]
    )
    return ChatService(pipeline, sink or build_event_sink(settings))
