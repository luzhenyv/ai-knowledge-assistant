#!/usr/bin/env python3
"""Front door for the document-preprocessing skill: best-effort `source -> PDF`.

`aka prep` already handles `.pdf` (passthrough) and `.pages` (Apple Pages). This
script covers the formats it does not: Office documents (via LibreOffice headless)
and loose page images (combined into one PDF via Pillow). PDF is the single
intermediate every extractor reads, so getting here means the rest of the pipeline
just works.

Usage:
    python normalize_to_pdf.py report.docx
    python normalize_to_pdf.py slide1.png slide2.png        # -> one multi-page PDF
    python normalize_to_pdf.py deck.pptx --out var/prep/pdf

Output PDFs are written under var/prep/pdf/ (gitignored) and the path is printed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

OFFICE_SUFFIXES = {".docx", ".doc", ".pptx", ".ppt", ".odt", ".odp", ".rtf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}


def _office_to_pdf(src: Path, out_dir: Path) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError(
            f"Converting {src.name} needs LibreOffice (`soffice`), which was not found.\n"
            "Options: install LibreOffice (`brew install --cask libreoffice`), or export "
            "the file to PDF yourself and feed the PDF to `aka prep`."
        )
    result = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(src)],
        capture_output=True,
        text=True,
    )
    out = out_dir / (src.stem + ".pdf")
    if result.returncode != 0 or not out.exists():
        raise RuntimeError(f"LibreOffice failed for {src.name}: {result.stderr.strip()}")
    return out


def _images_to_pdf(images: list[Path], out_dir: Path) -> Path:
    try:
        from PIL import Image
    except ImportError as e:  # pragma: no cover - environment guard
        raise RuntimeError(
            "Combining images into a PDF needs Pillow. Install it with "
            "`uv sync --extra prep` (or `pip install pillow`)."
        ) from e

    frames = [Image.open(p).convert("RGB") for p in images]
    out = out_dir / (images[0].stem + ".pdf")
    frames[0].save(out, "PDF", save_all=True, append_images=frames[1:])
    return out


def _pages_to_pdf(src: Path, out_dir: Path) -> Path:
    # Reuse the project's Pages.app AppleScript rather than duplicating it.
    repo_src = Path(__file__).resolve().parents[4] / "src"
    sys.path.insert(0, str(repo_src))
    from aka.preprocess.normalize import PagesAppNormalizer  # noqa: E402
    from aka.preprocess.profile import PrepProfile  # noqa: E402

    return PagesAppNormalizer().to_pdf(src, PrepProfile(slug=src.stem, source_type="pages"), out_dir)


def normalize(sources: list[Path], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    suffixes = {p.suffix.lower() for p in sources}

    # Many images -> one PDF (page order = argument order).
    if suffixes <= IMAGE_SUFFIXES:
        return _images_to_pdf(sources, out_dir)

    if len(sources) != 1:
        raise SystemExit("Pass a single document, or several images to combine into one PDF.")
    src = sources[0]
    suffix = src.suffix.lower()

    if suffix == ".pdf":
        dest = out_dir / src.name
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        return dest
    if suffix == ".pages":
        return _pages_to_pdf(src, out_dir)
    if suffix in OFFICE_SUFFIXES:
        return _office_to_pdf(src, out_dir)
    raise SystemExit(f"Unsupported source type {suffix!r} for {src.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize a source document (or images) to PDF.")
    ap.add_argument("sources", nargs="+", type=Path, help="Source file(s). Multiple = images to combine.")
    ap.add_argument("--out", type=Path, default=Path("var/prep/pdf"), help="Output directory (default var/prep/pdf).")
    args = ap.parse_args()

    missing = [p for p in args.sources if not p.exists()]
    if missing:
        raise SystemExit(f"Not found: {', '.join(str(p) for p in missing)}")

    pdf = normalize(args.sources, args.out)
    print(pdf)


if __name__ == "__main__":
    main()
