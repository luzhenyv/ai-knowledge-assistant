"""Interface contracts (Protocols). Everything depends on these; they depend on
nothing but ``domain``. Swapping an implementation (FAISS->Chroma, Claude->Ollama)
is a one-line change in ``aka.pipeline.container`` because callers only ever see
these structural types.
"""

from aka.contracts.embedder import Embedder, Vector
from aka.contracts.eventsink import EventSink
from aka.contracts.generator import AnswerGenerator
from aka.contracts.guardrail import Decision, Guardrail
from aka.contracts.llm import LLM, Message
from aka.contracts.recommender import Recommender
from aka.contracts.retriever import Retriever
from aka.contracts.vectorstore import ScoredChunkId, VectorStore

__all__ = [
    "Embedder",
    "Vector",
    "EventSink",
    "AnswerGenerator",
    "Decision",
    "Guardrail",
    "LLM",
    "Message",
    "Recommender",
    "Retriever",
    "ScoredChunkId",
    "VectorStore",
]
