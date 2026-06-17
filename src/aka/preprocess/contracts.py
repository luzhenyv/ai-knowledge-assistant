"""Interface contracts for the preprocessing stages + the value objects that flow
between them. Implementations live in sibling modules; the pipeline depends only
on these Protocols, so extractors/structurers are swappable per material.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from aka.preprocess.profile import PrepProfile


@dataclass(frozen=True)
class ExtractedImage:
    """One image pulled out of a source document, before filtering/renaming."""

    path: Path  # where the raw extracted file currently lives
    page: int  # 1-based page it appeared on
    index: int  # order within the page
    width: int
    height: int
    alt: str = ""


@dataclass
class RawDoc:
    """Output of the extract stage: rough markdown + the images/pages it produced."""

    markdown: str
    embedded_images: list[ExtractedImage] = field(default_factory=list)
    page_images: list[Path] = field(default_factory=list)  # full-page rasters (vision path)
    page_count: int = 0


@dataclass
class StructuredDoc:
    """Output of the structure stage: clean markdown (with figure placeholders or
    normalized image links) + the images the markdown actually references.
    """

    title: str
    markdown: str
    images: list[ExtractedImage] = field(default_factory=list)


@runtime_checkable
class SourceNormalizer(Protocol):
    """Converts a source file to PDF (the single intermediate every extractor reads)."""

    def to_pdf(self, src: Path, profile: "PrepProfile", workdir: Path) -> Path:
        ...


@runtime_checkable
class Extractor(Protocol):
    """PDF -> rough markdown + extracted images + page rasters."""

    def extract(self, pdf: Path, profile: "PrepProfile", workdir: Path) -> RawDoc:
        ...


@runtime_checkable
class Structurer(Protocol):
    """RawDoc -> clean, heading-structured markdown ready for emission."""

    def structure(self, raw: RawDoc, profile: "PrepProfile") -> StructuredDoc:
        ...
