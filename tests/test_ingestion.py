from aka.domain.models import Document
from aka.ingestion.splitter import split_document

MD = """# Tool SOP

Intro line.

## 1. Install

Do the install.

![install shot](images/install.png)

## 2. Authorization

Log in here.
"""


def test_splitter_is_heading_aware_and_keeps_breadcrumb():
    doc = Document(id="d1", title="Tool SOP", source="t.md", text=MD)
    chunks = split_document(doc)
    paths = [c.section_path for c in chunks]
    # Preamble + two sections.
    assert "1. Install" in paths
    assert "2. Authorization" in paths


def test_splitter_attaches_images_to_their_section():
    doc = Document(id="d1", title="Tool SOP", source="t.md", text=MD)
    install = next(c for c in split_document(doc) if c.section_path == "1. Install")
    assert [im.path for im in install.images] == ["images/install.png"]
    # The authorization section has no image.
    auth = next(c for c in split_document(doc) if c.section_path == "2. Authorization")
    assert auth.images == ()
