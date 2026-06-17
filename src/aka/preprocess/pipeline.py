"""Orchestrates the preprocessing stages: normalize -> extract -> structure ->
images -> emit. Returns a PrepReport. Object construction (which structurer, which
LLM) is explicit here, mirroring the serving pipeline's container.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from aka.preprocess.contracts import Structurer
from aka.preprocess.emit import source_sha, write_output
from aka.preprocess.extract import select_extractor
from aka.preprocess.images import place_images
from aka.preprocess.normalize import select_normalizer
from aka.preprocess.profile import PrepProfile
from aka.preprocess.structure import (
    ClaudeVisionPageStructurer,
    DeterministicStructurer,
    PageStructurer,
    VisionLLMStructurer,
)

_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)


@dataclass
class PrepReport:
    slug: str
    out_dir: Path
    page_count: int
    headings: int
    images_kept: int
    images_dropped: int
    structurer: str

    def render(self) -> str:
        flags = " ⚠ no headings detected" if self.headings == 0 else ""
        return (
            f"prep[{self.slug}] -> {self.out_dir}\n"
            f"  pages={self.page_count} headings={self.headings} "
            f"images kept={self.images_kept} dropped={self.images_dropped} "
            f"structurer={self.structurer}{flags}"
        )


def _build_structurer(
    profile: PrepProfile,
    llm=None,
    page_structurer: PageStructurer | None = None,
) -> Structurer:
    if profile.structurer == "deterministic":
        return DeterministicStructurer()
    if profile.structurer == "vision-llm":
        ps = page_structurer
        if ps is None:
            if llm is None:
                raise RuntimeError(
                    "structurer 'vision-llm' needs an LLM. Pass one, or set the "
                    "ANTHROPIC_API_KEY and use the default Anthropic client."
                )
            ps = ClaudeVisionPageStructurer(llm)
        return VisionLLMStructurer(ps)
    raise ValueError(f"Unknown structurer {profile.structurer!r}")


def run_prep(
    source: str | Path,
    profile: PrepProfile,
    out_root: str | Path,
    workdir_root: str | Path,
    timestamp: str,
    llm=None,
    page_structurer: PageStructurer | None = None,
) -> PrepReport:
    source = Path(source)
    workdir = Path(workdir_root) / profile.slug
    out_dir = Path(out_root) / profile.slug

    normalizer = select_normalizer(source, profile)
    pdf = normalizer.to_pdf(source, profile, workdir / "pdf")

    extractor = select_extractor(profile)
    raw = extractor.extract(pdf, profile, workdir)

    structurer = _build_structurer(profile, llm=llm, page_structurer=page_structurer)
    structured = structurer.structure(raw, profile)

    placed = place_images(structured, profile, out_dir)

    provenance = {
        "slug": profile.slug,
        "title": structured.title,
        "source_sha256": source_sha(source),
        "source_name": source.name,
        "page_count": raw.page_count,
        "extractor": profile.extractor,
        "structurer": profile.structurer,
        "model": profile.llm.model if profile.structurer == "vision-llm" else None,
        "images_kept": placed.kept,
        "images_dropped": placed.dropped,
        "built_at": timestamp,
    }
    write_output(out_dir, placed.markdown, provenance)

    return PrepReport(
        slug=profile.slug,
        out_dir=out_dir,
        page_count=raw.page_count,
        headings=len(_HEADING.findall(placed.markdown)),
        images_kept=placed.kept,
        images_dropped=placed.dropped,
        structurer=profile.structurer,
    )
