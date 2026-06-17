"""Golden-set evaluation. This is how "answer accuracy" and "fewer hallucinations"
become measurable rather than asserted.

Per question it checks:
* retrieval hit@k — did a chunk from the expected section get retrieved?
* groundedness    — did the system answer vs. correctly refuse (escalate)?
* keyword presence — optional, did the answer mention expected terms?

Runs against the real serving pipeline, so it requires `aka build` to have run.
With the 'fake' LLM provider it is fully offline and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from aka.config.settings import Settings
from aka.pipeline.container import build_chat_service

GOLDEN_PATH = Path(__file__).parent / "golden.yaml"


@dataclass
class ItemResult:
    question: str
    retrieval_hit: bool
    grounded_ok: bool
    keywords_ok: bool

    @property
    def passed(self) -> bool:
        return self.retrieval_hit and self.grounded_ok and self.keywords_ok


@dataclass
class EvalReport:
    items: list[ItemResult]

    @property
    def passed(self) -> bool:
        return all(i.passed for i in self.items)

    def render(self) -> str:
        lines = ["Golden-set evaluation", "=" * 40]
        for i in self.items:
            flag = "PASS" if i.passed else "FAIL"
            lines.append(
                f"[{flag}] hit@k={i.retrieval_hit!s:<5} grounded={i.grounded_ok!s:<5} "
                f"kw={i.keywords_ok!s:<5}  {i.question}"
            )
        n = len(self.items)
        hits = sum(i.retrieval_hit for i in self.items)
        gnd = sum(i.grounded_ok for i in self.items)
        lines += [
            "-" * 40,
            f"retrieval hit@k : {hits}/{n}",
            f"groundedness    : {gnd}/{n}",
            f"overall         : {'PASS' if self.passed else 'FAIL'} "
            f"({sum(i.passed for i in self.items)}/{n})",
        ]
        return "\n".join(lines)


def run_eval(settings: Settings, golden_path: Path = GOLDEN_PATH) -> EvalReport:
    golden = yaml.safe_load(golden_path.read_text()) or []
    service = build_chat_service(settings)

    results: list[ItemResult] = []
    for item in golden:
        result = service.ask(item["question"])
        ctx = result.context
        answer = ctx.answer

        expect_grounded = bool(item.get("expect_grounded", True))
        grounded_ok = bool(answer and answer.grounded) == expect_grounded

        # Retrieval hit only meaningful when we expect an answer.
        expect_section = (item.get("expect_section") or "").lower()
        if expect_grounded and expect_section:
            retrieval_hit = any(
                expect_section in c.section_path.lower() for c in ctx.chunks
            )
        else:
            retrieval_hit = True

        keywords = [k.lower() for k in item.get("expect_keywords", [])]
        text = (answer.text if answer else "").lower()
        keywords_ok = all(k in text for k in keywords) if (expect_grounded and keywords) else True

        results.append(
            ItemResult(
                question=item["question"],
                retrieval_hit=retrieval_hit,
                grounded_ok=grounded_ok,
                keywords_ok=keywords_ok,
            )
        )
    return EvalReport(items=results)
