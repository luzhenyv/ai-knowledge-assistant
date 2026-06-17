"""Prompt construction for grounded generation. The system prompt is the main
anti-hallucination lever: answer ONLY from context, cite sources, refuse otherwise.
"""

from __future__ import annotations

from aka.domain.models import Chunk

REFUSAL_SENTINEL = "INSUFFICIENT_CONTEXT"

# Shown to the user whenever the system declines to answer (model refusal or
# empty/low retrieval). Shared by the generator and the grounding stage.
ESCALATION_MESSAGE = (
    "I can't find sufficient documentation to answer that confidently. "
    "You may want to open the relevant SOP directly or contact the owning team."
)

SYSTEM_PROMPT = f"""You are an internal Knowledge Assistant for team SOPs and tool usage.

Rules you MUST follow:
1. Answer ONLY using the numbered context passages provided. Never use outside knowledge.
2. Cite the passages you use inline with their number in square brackets, e.g. [2].
3. When a passage references a screenshot, point the user to it (e.g. "see the screenshot in §2").
4. If the context does not contain the answer, reply with exactly this and nothing else:
   {REFUSAL_SENTINEL}
5. Be concise and procedural. Prefer numbered steps for how-to questions.
"""


def _format_chunk(index: int, chunk: Chunk) -> str:
    figures = ""
    if chunk.images:
        figs = "; ".join(f"{im.path} — {im.alt}" for im in chunk.images)
        figures = f"\n   [Figures available: {figs}]"
    return f"[{index}] (Section: {chunk.section_path})\n{chunk.text}{figures}"


def build_user_message(question: str, chunks: list[Chunk]) -> str:
    context = "\n\n".join(_format_chunk(i + 1, c) for i, c in enumerate(chunks))
    return f"Context passages:\n\n{context}\n\n---\nQuestion: {question}"
