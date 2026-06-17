"""OFFLINE preprocessing: source documents (.pdf/.pages) -> aka-ingestible markdown.

This bounded context sits *upstream* of ingestion. It converts arbitrary source
files into the ``docs/<slug>/sop.md`` + ``images/`` contract that
``aka.ingestion`` already consumes, so the RAG never learns about source formats.

Five swappable stages behind Protocols (``contracts.py``), driven by a per-material
YAML profile (``profile.py``):

    normalize -> extract -> structure -> images -> emit

Markdown is the human-reviewable, editable intermediate; raw sources never enter
the repo (see .gitignore).
"""

from aka.preprocess.pipeline import PrepReport, run_prep

__all__ = ["PrepReport", "run_prep"]
