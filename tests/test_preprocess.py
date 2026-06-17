"""Preprocessing pipeline tests.

Most run with only PIL (always available). The full round-trip test needs the
optional ``prep`` extra (pymupdf4llm) and skips cleanly otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aka.preprocess.contracts import ExtractedImage, RawDoc, StructuredDoc
from aka.preprocess.images import place_images
from aka.preprocess.normalize import PdfPassthrough, select_normalizer
from aka.preprocess.profile import PrepProfile
from aka.preprocess.structure import (
    FIG_PLACEHOLDER,
    DeterministicStructurer,
    VisionLLMStructurer,
)


def _png(path: Path, w: int, h: int) -> Path:
    from PIL import Image

    Image.new("RGB", (w, h), (123, 150, 200)).save(path)
    return path


def _profile(**kw) -> PrepProfile:
    base = {"slug": "demo"}
    base.update(kw)
    return PrepProfile(**base)


# ---- deterministic structurer -----------------------------------------------

def test_deterministic_coerces_numbered_headings_and_strips_noise():
    raw = RawDoc(markdown="1. Install\nDo the install.\n-----\n12\n2. Authorization\nSign in.")
    prof = _profile(headings=[{"pattern": r"^\d+\.?\s+\S", "level": 2}], title="Demo SOP")
    out = DeterministicStructurer().structure(raw, prof)
    assert "## 1. Install" in out.markdown
    assert "## 2. Authorization" in out.markdown
    assert "-----" not in out.markdown      # page separator stripped
    assert "\n12\n" not in out.markdown      # bare page number stripped
    assert out.markdown.startswith("# Demo SOP")  # H1 ensured


# ---- image filtering + naming ------------------------------------------------

def test_place_images_filters_and_renames_deterministic(tmp_path):
    big = _png(tmp_path / "a.png", 200, 160)
    small = _png(tmp_path / "b.png", 20, 20)
    images = [
        ExtractedImage(path=big, page=1, index=1, width=200, height=160),
        ExtractedImage(path=small, page=1, index=2, width=20, height=20),
    ]
    md = "# T\n\n## Step\n\n![](a.png)\n\n![](b.png)\n"
    placed = place_images(StructuredDoc(title="T", markdown=md, images=images), _profile(), tmp_path / "out")

    assert placed.kept == 1 and placed.dropped == 1
    assert (tmp_path / "out" / "images" / "p01-fig01.png").exists()
    assert "images/p01-fig01.png" in placed.markdown
    assert "b.png" not in placed.markdown  # dropped image's link removed


def test_place_images_resolves_vision_placeholders(tmp_path):
    big = _png(tmp_path / "fig.png", 300, 200)
    images = [ExtractedImage(path=big, page=1, index=1, width=300, height=200)]
    md = f"# T\n\n<!--PAGE:1-->\n## Step one\n\n{FIG_PLACEHOLDER}\n\nmore text"
    placed = place_images(StructuredDoc(title="T", markdown=md, images=images), _profile(), tmp_path / "out")

    assert placed.kept == 1
    assert "images/p01-fig01.png" in placed.markdown
    assert FIG_PLACEHOLDER not in placed.markdown
    assert "<!--PAGE:1-->" not in placed.markdown  # marker stripped


# ---- vision structurer (offline via a fake page structurer) ------------------

class _FakePageStructurer:
    def structure_page(self, image_path, profile):
        return f"## Section for {image_path.stem}\n{FIG_PLACEHOLDER}"


def test_vision_structurer_assembles_pages(tmp_path):
    raw = RawDoc(markdown="", page_images=[tmp_path / "page-001.png", tmp_path / "page-002.png"])
    out = VisionLLMStructurer(_FakePageStructurer()).structure(raw, _profile(title="V"))
    assert out.markdown.startswith("# V")
    assert "<!--PAGE:1-->" in out.markdown and "<!--PAGE:2-->" in out.markdown
    assert out.markdown.count(FIG_PLACEHOLDER) == 2


# ---- normalize selection / guard --------------------------------------------

def test_select_normalizer_pdf_passthrough():
    assert isinstance(select_normalizer(Path("x.pdf"), _profile()), PdfPassthrough)


def test_pages_normalizer_errors_without_pages_app(tmp_path, monkeypatch):
    import aka.preprocess.normalize as norm

    monkeypatch.setattr(norm, "_pages_app_available", lambda: False)
    with pytest.raises(RuntimeError, match="requires Apple Pages"):
        norm.PagesAppNormalizer().to_pdf(tmp_path / "x.pages", _profile(source_type="pages"), tmp_path)


# ---- full round-trip through the real ingestion contract (needs prep extra) --

def test_round_trip_pdf_to_ingestible_markdown(tmp_path):
    fitz = pytest.importorskip("fitz")
    pytest.importorskip("pymupdf4llm")
    from aka.ingestion.loader import load_documents
    from aka.ingestion.splitter import split_document
    from aka.preprocess.pipeline import run_prep

    # Build a tiny 2-page PDF with headings + an embedded image.
    img = _png(tmp_path / "shot.png", 240, 160)
    doc = fitz.open()
    for title in ("1. Install", "2. Authorization"):
        page = doc.new_page()
        page.insert_text((72, 72), title, fontsize=20)
        page.insert_text((72, 110), "Follow these steps.", fontsize=12)
        page.insert_image(fitz.Rect(72, 130, 312, 290), filename=str(img))
    pdf = tmp_path / "manual.pdf"
    doc.save(pdf)
    doc.close()

    prof = _profile(
        slug="rt", title="Round Trip SOP",
        headings=[{"pattern": r"^\d+\.?\s+\S", "level": 2}],
    )
    report = run_prep(
        source=pdf, profile=prof,
        out_root=tmp_path / "docs", workdir_root=tmp_path / "var" / "prep",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    md = tmp_path / "docs" / "rt" / "sop.md"
    assert md.exists()
    assert report.images_kept >= 1

    # The emitter's output must parse through the REAL ingestion contract.
    docs = load_documents(tmp_path / "docs")
    chunks = [c for d in docs for c in split_document(d)]
    sections = {c.section_path for c in chunks}
    assert any("Install" in s for s in sections)
    assert any(c.images for c in chunks), "image refs must survive into chunks"
