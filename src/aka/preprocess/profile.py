"""Per-material preprocessing profile — the single fine-tune knob.

One YAML file per source document (or family of documents). Everything that varies
between materials lives here, never in code, so adapting to a new SOP is editing a
profile and re-running, not changing the pipeline.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ImageRules(BaseModel):
    # Drop sub-threshold images (icons, bullets, rule lines, decorations).
    min_width: int = 80
    min_height: int = 80
    keep_formats: list[str] = Field(default_factory=lambda: ["png", "jpeg", "jpg"])


class HeadingRule(BaseModel):
    pattern: str  # regex matched against a line (case-insensitive)
    level: int = 2  # markdown heading level to coerce the line to


class LLMRules(BaseModel):
    model: str = "claude-sonnet-4-6"
    dpi: int = 150  # page rasterization resolution for the vision pass
    prompt_profile: str = "sop"


class PrepProfile(BaseModel):
    slug: str  # output dir name: docs/<slug>/
    title: str | None = None  # inferred from content if omitted
    source_type: str = "auto"  # auto | pdf | pages
    extractor: str = "pymupdf4llm"
    structurer: str = "deterministic"  # deterministic | vision-llm
    pages: str = "all"  # "all" or a range like "2-14"
    images: ImageRules = Field(default_factory=ImageRules)
    headings: list[HeadingRule] = Field(default_factory=list)
    llm: LLMRules = Field(default_factory=LLMRules)

    def page_range(self) -> tuple[int, int] | None:
        """Parse ``pages`` into 1-based inclusive (start, end), or None for all."""
        if self.pages == "all":
            return None
        lo, _, hi = self.pages.partition("-")
        return (int(lo), int(hi or lo))


def load_profile(path: str | Path) -> PrepProfile:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return PrepProfile(**data)
