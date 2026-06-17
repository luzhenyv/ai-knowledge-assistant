"""The deterministic runner + the application service that wraps it.

Pipeline.run iterates stages, short-circuiting on rejection. ChatService owns the
cross-cutting concerns the stages must not know about: timing, id/timestamp
generation, and publishing the post-request event to the sink.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from aka.contracts.eventsink import EventSink
from aka.domain.events import InteractionLogged
from aka.domain.models import ChatContext
from aka.pipeline.stage import Stage


class Pipeline:
    def __init__(self, stages: list[Stage]) -> None:
        self._stages = stages

    def run(self, ctx: ChatContext) -> ChatContext:
        for stage in self._stages:
            ctx = stage.execute(ctx)
            if ctx.rejected:
                break
        return ctx


@dataclass
class ChatResult:
    interaction_id: str
    context: ChatContext


class ChatService:
    """Stateless per-request entry point. Each call is independent (no memory)."""

    def __init__(self, pipeline: Pipeline, sink: EventSink) -> None:
        self._pipeline = pipeline
        self._sink = sink

    def ask(self, question: str) -> ChatResult:
        interaction_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        ctx = self._pipeline.run(ChatContext(question=question))
        latency_ms = int((time.perf_counter() - started) * 1000)

        self._sink.emit(self._build_event(interaction_id, ctx, latency_ms))
        return ChatResult(interaction_id=interaction_id, context=ctx)

    @staticmethod
    def _build_event(interaction_id: str, ctx: ChatContext, latency_ms: int) -> InteractionLogged:
        answer = ctx.answer
        citations = (
            tuple(f"{c.doc_title} :: {c.section_path}" for c in answer.citations)
            if answer
            else ()
        )
        return InteractionLogged(
            interaction_id=interaction_id,
            question=ctx.question,
            answer_text=answer.text if answer else "",
            grounded=bool(answer and answer.grounded),
            rejected=ctx.rejected,
            citations=citations,
            chunk_ids=tuple(c.id for c in ctx.chunks),
            recommendations=tuple(ctx.recommendations),
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={k: v for k, v in ctx.metadata.items() if k != "score"},
        )
