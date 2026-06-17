"""AI Knowledge Assistant (aka) — a citation-grounded RAG prototype.

The package is organised into three bounded contexts that share only ``domain``
(value objects) and ``contracts`` (Protocols):

* ingestion  — OFFLINE: markdown + images -> chunks -> embeddings -> index
* serving    — ONLINE:  question -> guard -> retrieve -> ground -> generate -> recommend
* observability — append-only event + feedback log for later analysis

Modules never import each other. They communicate through ``ChatContext`` during a
request and through events afterwards. Object construction happens in one place:
``aka.pipeline.container``.
"""

__version__ = "0.1.0"
