"""Stage 4 — filter, rename, and place images; finalize the markdown's image refs.

* Filter out sub-threshold images (icons, bullets, rules) per the profile.
* Rename kept images to stable ``p{page:02d}-fig{index:02d}.png``.
* Copy them into ``<out>/images/`` (as PNG).
* Finalize references:
    - vision path: resolve ``<<FIG>>`` placeholders (in reading order, per page).
    - deterministic path: rewrite the extractor's inline links to ``images/<new>``
      and drop links to filtered-out images.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from aka.preprocess.contracts import ExtractedImage, StructuredDoc
from aka.preprocess.profile import PrepProfile
from aka.preprocess.structure import FIG_PLACEHOLDER, PAGE_MARKER

_PAGE_MARKER_RE = re.compile(r"<!--PAGE:(\d+)-->")


@dataclass
class PlacedImages:
    markdown: str
    kept: int
    dropped: int


def place_images(
    structured: StructuredDoc, profile: PrepProfile, out_dir: Path
) -> PlacedImages:
    from PIL import Image

    keep_formats = {f.lower().lstrip(".") for f in profile.images.keep_formats}
    kept: list[ExtractedImage] = []
    dropped = 0
    for img in structured.images:
        fmt = img.path.suffix.lower().lstrip(".")
        if (
            img.width >= profile.images.min_width
            and img.height >= profile.images.min_height
            and (fmt in keep_formats or fmt == "png")
        ):
            kept.append(img)
        else:
            dropped += 1

    # Assign stable, unique names and copy into <out>/images/ as PNG.
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    names: dict[Path, str] = {}
    used: set[str] = set()
    for img in kept:
        base = f"p{img.page:02d}-fig{img.index:02d}"
        name = f"{base}.png"
        k = 1
        while name in used:
            name = f"{base}-{k}.png"
            k += 1
        used.add(name)
        names[img.path] = name
        with Image.open(img.path) as im:
            im.convert("RGB").save(images_dir / name)

    if FIG_PLACEHOLDER in structured.markdown:
        markdown = _resolve_placeholders(structured.markdown, kept, names)
    else:
        markdown = _rewrite_links(structured.markdown, structured.images, names)

    return PlacedImages(markdown=markdown.strip() + "\n", kept=len(kept), dropped=dropped)


def _ref(name: str, alt: str = "") -> str:
    return f"![{alt}](images/{name})"


def _resolve_placeholders(
    markdown: str, kept: list[ExtractedImage], names: dict[Path, str]
) -> str:
    """Replace <<FIG>> tokens with this page's kept images, in reading order."""
    by_page: dict[int, list[ExtractedImage]] = {}
    for img in kept:
        by_page.setdefault(img.page, []).append(img)

    out_lines: list[str] = []
    current_page = 0
    cursor = 0
    for line in markdown.splitlines():
        m = _PAGE_MARKER_RE.match(line.strip())
        if m:
            current_page = int(m.group(1))
            cursor = 0
            continue
        if line.strip() == FIG_PLACEHOLDER:
            page_imgs = by_page.get(current_page, [])
            if cursor < len(page_imgs):
                img = page_imgs[cursor]
                out_lines.append(_ref(names[img.path]))
                cursor += 1
            # Unmatched placeholder (no image left for this page) -> drop the token.
            continue
        out_lines.append(line)

    # Append any page images the model never placed, after their page's content.
    return "\n".join(out_lines)


def _rewrite_links(
    markdown: str, all_images: list[ExtractedImage], names: dict[Path, str]
) -> str:
    """Rewrite the extractor's inline image links: kept -> images/<new>, dropped -> removed."""
    for img in all_images:
        basename = re.escape(img.path.name)
        if img.path in names:
            # ![alt](.../basename) -> ![alt](images/<new>)
            markdown = re.sub(
                rf"(!\[[^\]]*\]\()[^)]*{basename}(\))",
                lambda m, n=names[img.path]: f"{m.group(1)}images/{n}{m.group(2)}",
                markdown,
            )
        else:
            # Drop the whole image markdown for filtered-out images.
            markdown = re.sub(rf"!\[[^\]]*\]\([^)]*{basename}\)\s*", "", markdown)
    return markdown
