"""Grounded answer generator. Depends only on the LLM contract.

Citations are assembled from the passages the model actually cited (inline [n]),
falling back to all supplied passages if it cited none. The returned Answer carries
its own evidence and ``grounded`` flag so later stages never reconstruct them.
"""

from __future__ import annotations

import re

from aka.contracts.llm import LLM
from aka.domain.models import Answer, Chunk, Citation
from aka.generation.prompts import (
    ESCALATION_MESSAGE,
    REFUSAL_SENTINEL,
    SYSTEM_PROMPT,
    build_user_message,
)

_CITE = re.compile(r"\[(\d+)\]")


class GroundedAnswerGenerator:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def generate(self, question: str, chunks: list[Chunk]) -> Answer:
        if not chunks:
            return Answer(text=ESCALATION_MESSAGE, citations=(), grounded=False)

        user = build_user_message(question, chunks)
        raw = self._llm.complete(SYSTEM_PROMPT, [{"role": "user", "content": user}]).strip()

        if REFUSAL_SENTINEL in raw:
            return Answer(text=ESCALATION_MESSAGE, citations=(), grounded=False)

        citations = _assemble_citations(raw, chunks)
        return Answer(text=raw, citations=citations, grounded=True)


def _assemble_citations(answer_text: str, chunks: list[Chunk]) -> tuple[Citation, ...]:
    cited_indices = {int(n) for n in _CITE.findall(answer_text)}
    # Map 1-based citation markers to the supplied passages; ignore out-of-range.
    used = [chunks[i - 1] for i in sorted(cited_indices) if 1 <= i <= len(chunks)]
    if not used:
        used = chunks  # the model answered from context but didn't number it
    return tuple(
        Citation(
            doc_title=c.doc_title,
            section_path=c.section_path,
            chunk_id=c.id,
            images=c.images,
        )
        for c in used
    )
