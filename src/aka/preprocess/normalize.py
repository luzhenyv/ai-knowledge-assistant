"""Stage 1 — normalize any source to PDF, the single intermediate every extractor
reads. Unifying on PDF means we maintain ONE good extractor instead of a fragile
parser per format.

* PdfPassthrough  — .pdf is already our intermediate.
* PagesAppNormalizer — .pages -> PDF by driving Pages.app via AppleScript. Runs on
  a Mac with Pages installed (Apple ships no headless iWork converter; LibreOffice
  is the alternative if Pages is unavailable).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from aka.preprocess.profile import PrepProfile


class PdfPassthrough:
    def to_pdf(self, src: Path, profile: PrepProfile, workdir: Path) -> Path:
        return src


# AppleScript: open the doc, export to PDF, close without saving. Placeholders are
# filled with absolute POSIX paths.
_EXPORT_SCRIPT = '''
tell application "Pages"
    set theDoc to open POSIX file "{src}"
    export theDoc to POSIX file "{out}" as PDF
    close theDoc saving no
end tell
'''


class PagesAppNormalizer:
    def to_pdf(self, src: Path, profile: PrepProfile, workdir: Path) -> Path:
        if not _pages_app_available():
            raise RuntimeError(
                "Converting .pages requires Apple Pages (this machine has neither "
                "Pages.app nor osascript access to it).\n"
                "Options: run on a Mac with Pages installed, install LibreOffice and "
                "use `soffice --headless --convert-to pdf`, or export the file to PDF "
                "yourself and feed the PDF to `aka prep`."
            )
        workdir.mkdir(parents=True, exist_ok=True)
        out = workdir / (src.stem + ".pdf")
        script = _EXPORT_SCRIPT.format(src=src.resolve(), out=out.resolve())
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True
        )
        if result.returncode != 0 or not out.exists():
            raise RuntimeError(f"Pages export failed for {src}: {result.stderr.strip()}")
        return out


def _pages_app_available() -> bool:
    return shutil.which("osascript") is not None and Path("/Applications/Pages.app").exists()


def select_normalizer(src: Path, profile: PrepProfile):
    kind = profile.source_type
    if kind == "auto":
        kind = src.suffix.lower().lstrip(".")
    if kind == "pdf":
        return PdfPassthrough()
    if kind in ("pages",):
        return PagesAppNormalizer()
    raise ValueError(f"Unsupported source_type {kind!r} for {src.name}")
