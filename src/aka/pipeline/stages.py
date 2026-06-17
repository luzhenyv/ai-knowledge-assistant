"""The concrete pipeline stages. Each depends only on a contract (injected) and on
ChatContext. Order and composition live in the container, not here.
"""

from __future__ import annotations

from aka.contracts.generator import AnswerGenerator
from aka.contracts.guardrail import Guardrail
from aka.contracts.recommender import Recommender
from aka.contracts.retriever import Retriever
from aka.domain.models import Answer, ChatContext
from aka.generation.prompts import ESCALATION_MESSAGE


class GuardStage:
    """Thin scope check. Rejects clearly out-of-scope questions before retrieval."""

    def __init__(self, guard: Guardrail) -> None:
        self._guard = guard

    def execute(self, ctx: ChatContext) -> ChatContext:
        decision = self._guard.check(ctx.question)
        if not decision.allowed:
            ctx.rejected = True
            ctx.answer = Answer(text=decision.reason, citations=(), grounded=False)
            ctx.metadata["reject_reason"] = "guardrail"
        return ctx


class RetrievalStage:
    def __init__(self, retriever: Retriever, top_k: int) -> None:
        self._retriever = retriever
        self._top_k = top_k

    def execute(self, ctx: ChatContext) -> ChatContext:
        ctx.chunks = self._retriever.retrieve(ctx.question, k=self._top_k)
        ctx.metadata["top_score"] = max(
            (c.metadata.get("score", 0.0) for c in ctx.chunks), default=0.0
        )
        return ctx


class GroundingStage:
    """Primary anti-hallucination gate: if nothing relevant retrieved (empty, or
    best score below the floor), escalate instead of letting the model guess.
    """

    def __init__(self, relevance_floor: float) -> None:
        self._floor = relevance_floor

    def execute(self, ctx: ChatContext) -> ChatContext:
        top_score = ctx.metadata.get("top_score", 0.0)
        if not ctx.chunks or top_score < self._floor:
            ctx.rejected = True
            ctx.answer = Answer(text=ESCALATION_MESSAGE, citations=(), grounded=False)
            ctx.metadata["reject_reason"] = "low_relevance"
        return ctx


class GenerateStage:
    def __init__(self, generator: AnswerGenerator) -> None:
        self._generator = generator

    def execute(self, ctx: ChatContext) -> ChatContext:
        ctx.answer = self._generator.generate(ctx.question, ctx.chunks)
        return ctx


class RecommendStage:
    """Best-effort related topics. Only runs for grounded answers; never blocks."""

    def __init__(self, recommender: Recommender) -> None:
        self._recommender = recommender

    def execute(self, ctx: ChatContext) -> ChatContext:
        if ctx.answer is not None and ctx.answer.grounded:
            ctx.recommendations = self._recommender.recommend(ctx.question, ctx.chunks)
        return ctx
