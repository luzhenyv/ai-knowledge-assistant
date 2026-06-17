"""Stage 2 — PDF -> rough markdown + extracted images (+ page rasters for vision).

Default extractor is pymupdf4llm (purpose-built for PDF->markdown RAG ingestion):
it writes embedded images to disk and references them inline in the markdown, which
gives us figure *placement* for free on the deterministic path. Heavy imports are
lazy so the core package works without the optional ``prep`` extra installed.
"""

from __future__ import annotations

import re
from pathlib import Path

from aka.preprocess.contracts import ExtractedImage, RawDoc
from aka.preprocess.profile import PrepProfile

# pymupdf4llm names written images with the page + an index/xref in the stem.
_PAGE_IDX = re.compile(r"-(\d+)-(\d+)\.\w+$")


class PyMuPDF4LLMExtractor:
    def extract(self, pdf: Path, profile: PrepProfile, workdir: Path) -> RawDoc:
        import fitz  # PyMuPDF, via pymupdf4llm
        import pymupdf4llm
        from PIL import Image

        img_dir = workdir / "images_raw"
        img_dir.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(pdf)
        page_count = doc.page_count
        rng = profile.page_range()
        pages = None if rng is None else list(range(rng[0] - 1, min(rng[1], page_count)))

        markdown = pymupdf4llm.to_markdown(
            pdf,
            pages=pages,
            write_images=True,
            image_path=str(img_dir),
            image_format="png",
            dpi=profile.llm.dpi,
        )

        embedded: list[ExtractedImage] = []
        for order, img_path in enumerate(sorted(img_dir.glob("*.png")), start=1):
            try:
                with Image.open(img_path) as im:
                    w, h = im.size
            except Exception:
                continue
            page, idx = _parse_page_idx(img_path.name, order)
            embedded.append(
                ExtractedImage(path=img_path, page=page, index=idx, width=w, height=h)
            )

        page_images: list[Path] = []
        if profile.structurer == "vision-llm":
            page_images = _rasterize_pages(doc, pages, profile.llm.dpi, workdir / "pages")

        doc.close()
        return RawDoc(
            markdown=markdown,
            embedded_images=embedded,
            page_images=page_images,
            page_count=page_count,
        )


def _parse_page_idx(name: str, order: int) -> tuple[int, int]:
    m = _PAGE_IDX.search(name)
    if m:
        return int(m.group(1)) + 1, int(m.group(2))
    return order, order  # best-effort fallback


def _rasterize_pages(doc, pages, dpi: int, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    indices = pages if pages is not None else range(doc.page_count)
    out: list[Path] = []
    for i in indices:
        pix = doc[i].get_pixmap(dpi=dpi)
        path = out_dir / f"page-{i + 1:03d}.png"
        pix.save(path)
        out.append(path)
    return out


def select_extractor(profile: PrepProfile):
    if profile.extractor == "pymupdf4llm":
        return PyMuPDF4LLMExtractor()
    # DoclingExtractor would slot in here (future optional alternative).
    raise ValueError(f"Unknown extractor {profile.extractor!r}")
