#!/usr/bin/env python3
"""Acceptance oracle for the document-preprocessing skill.

Runs the *real* ingestion code (`aka.ingestion.loader.load_documents` +
`aka.ingestion.splitter.split_document`) over a generated `docs/<slug>/` and asserts
the output honors the ingestion contract:

  * exactly one `# H1` title,
  * at least one section heading (so the splitter produces real chunks),
  * every `![alt](images/..)` reference resolves on disk.

This is the same code the rest of the system uses, so passing here means `aka build`
will ingest the doc faithfully. Works for both the `aka prep` path and hand-authored
output (skill §4, step 5).

Usage:
    python check_contract.py docs/my-slug      # one document folder
    python check_contract.py docs              # every document under docs/

Exits non-zero if any document fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the project's `aka` package importable regardless of cwd.
_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO / "src"))

from aka.ingestion.loader import load_documents  # noqa: E402
from aka.ingestion.splitter import split_document  # noqa: E402


def _check_one(md_path: Path) -> list[str]:
    """Return a list of contract violations for a single sop.md (empty == ok)."""
    text = md_path.read_text(encoding="utf-8")
    problems: list[str] = []

    h1 = [ln for ln in text.splitlines() if ln.strip().startswith("# ")]
    if len(h1) != 1:
        problems.append(f"expected exactly one `# H1`, found {len(h1)}")

    # Reuse the real splitter so "heading" means exactly what ingestion thinks it means.
    docs = load_documents(md_path.parent)
    doc = next((d for d in docs if d.source == md_path.name), None)
    chunks = split_document(doc) if doc else []
    headings = {c.section_path for c in chunks if c.section_path != (doc.title if doc else "")}
    if not headings:
        problems.append("no section headings — splitter would yield no real chunks")

    base = md_path.parent
    for c in chunks:
        for img in c.images:
            ref = img.path
            if ref.startswith(("http://", "https://")):
                continue
            if not (base / ref).exists():
                problems.append(f"image ref does not resolve: {ref}")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="Check generated docs against the ingestion contract.")
    ap.add_argument("target", type=Path, help="A docs/<slug> folder, or docs/ to check all.")
    args = ap.parse_args()

    target: Path = args.target
    if not target.exists():
        raise SystemExit(f"Not found: {target}")

    sop_files = sorted(target.rglob("sop.md")) if target.is_dir() else []
    if not sop_files:
        raise SystemExit(f"No sop.md found under {target}")

    failed = 0
    for md in sop_files:
        slug = md.parent.name
        problems = _check_one(md)
        if problems:
            failed += 1
            print(f"FAIL  {slug}")
            for p in problems:
                print(f"        - {p}")
        else:
            print(f"OK    {slug}")

    if failed:
        print(f"\n{failed} document(s) failed the contract.")
        sys.exit(1)
    print(f"\nAll {len(sop_files)} document(s) honor the ingestion contract.")


if __name__ == "__main__":
    main()
