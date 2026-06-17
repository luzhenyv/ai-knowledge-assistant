"""OFFLINE context: markdown + images -> chunks -> embeddings -> index + manifest.

This package has no dependency on the serving pipeline; it only produces the
artifacts the retriever later reads.
"""

from aka.ingestion.indexer import IngestReport, build_index
from aka.ingestion.loader import load_documents
from aka.ingestion.splitter import split_document

__all__ = ["IngestReport", "build_index", "load_documents", "split_document"]
