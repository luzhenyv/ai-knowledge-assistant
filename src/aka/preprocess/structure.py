"""Stage 3 — RawDoc -> clean, heading-structured markdown.

* DeterministicStructurer (default): heuristic cleanup of the extractor's markdown —
  coerce numbered SOP headings to real levels, strip page-separator/footer noise,
  infer the title. Free and reproducible. Leaves image links for the images stage.
* VisionLLMStructurer (opt-in): Claude reads each page raster and emits clean
  markdown with ``<<FIG>>`` placeholders where screenshots belong. Best for
  annotated, screenshot-heavy SOPs. Injected page-structurer keeps it testable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from aka.preprocess.contracts import RawDoc, StructuredDoc
from aka.preprocess.profile import PrepProfile

_MD_HEADING = re.compile(r"^#{1,6}\s")
_IMAGE_LINE = re.compile(r"^!\[")
_PAGE_SEP = re.compile(r"^\s*-{3,}\s*$")  # pymupdf4llm page separator / hr
_NOISE = re.compile(r"^\s*(page\s+)?\d+\s*$", re.IGNORECASE)  # bare page numbers


class DeterministicStructurer:
    def structure(self, raw: RawDoc, profile: PrepProfile) -> StructuredDoc:
        rules = [(re.compile(r.pattern, re.IGNORECASE), r.level) for r in profile.headings]
        out: list[str] = []
        for line in raw.markdown.splitlines():
            if _PAGE_SEP.match(line) or _NOISE.match(line):
                continue
            if line.strip() and not _MD_HEADING.match(line) and not _IMAGE_LINE.match(line):
                line = _maybe_heading(line, rules)
            out.append(line)

        body = _collapse_blank_lines("\n".join(out)).strip()
        title = profile.title or _infer_title(body, profile.slug)
        if not body.startswith("# "):
            body = f"# {title}\n\n{body}"
        return StructuredDoc(title=title, markdown=body, images=list(raw.embedded_images))


def _maybe_heading(line: str, rules: list[tuple[re.Pattern, int]]) -> str:
    stripped = line.strip()
    # Only coerce short, heading-like lines (avoid turning a paragraph into a heading).
    if len(stripped) > 80:
        return line
    for pat, level in rules:
        if pat.match(stripped):
            return f"{'#' * level} {stripped}"
    return line


def _infer_title(markdown: str, slug: str) -> str:
    for line in markdown.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            return m.group(1).strip()
    return slug.replace("-", " ").title()


def _collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)


# ---- vision path -------------------------------------------------------------

FIG_PLACEHOLDER = "<<FIG>>"
PAGE_MARKER = "<!--PAGE:{n}-->"

VISION_SYSTEM = """You convert one page of an internal SOP into clean GitHub-flavored markdown.
Rules:
- Output markdown for THIS page only. No commentary, no code fences around the whole answer.
- Use ## / ### for section headings; use numbered lists for procedural steps.
- Where the page shows a screenshot, figure, or UI image, put the token <<FIG>> on its own line
  at that position (one token per image, in reading order).
- Do not invent content that is not visible on the page."""


@runtime_checkable
class PageStructurer(Protocol):
    def structure_page(self, image_path: Path, profile: PrepProfile) -> str:
        ...


class VisionLLMStructurer:
    def __init__(self, page_structurer: PageStructurer) -> None:
        self._page = page_structurer

    def structure(self, raw: RawDoc, profile: PrepProfile) -> StructuredDoc:
        blocks: list[str] = []
        for n, page_img in enumerate(raw.page_images, start=1):
            md = self._page.structure_page(page_img, profile).strip()
            blocks.append(f"{PAGE_MARKER.format(n=n)}\n{md}")
        body = _collapse_blank_lines("\n\n".join(blocks)).strip()
        title = profile.title or _infer_title(body, profile.slug)
        if not body.startswith("# "):
            body = f"# {title}\n\n{body}"
        return StructuredDoc(title=title, markdown=body, images=list(raw.embedded_images))


class ClaudeVisionPageStructurer:
    """Real page structurer backed by the Anthropic vision helper."""

    def __init__(self, llm) -> None:  # llm: aka.llm.AnthropicLLM
        self._llm = llm

    def structure_page(self, image_path: Path, profile: PrepProfile) -> str:
        return self._llm.complete_with_images(
            system=VISION_SYSTEM,
            prompt="Convert this SOP page to markdown following the rules.",
            image_paths=[image_path],
        )
