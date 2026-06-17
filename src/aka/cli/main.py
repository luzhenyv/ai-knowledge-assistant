"""`aka` command-line interface: build / validate / stats / chat / feedback / eval.

Thin layer — it only loads settings, asks the container to compose objects, and
prints. No business logic lives here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from aka.config.settings import load_settings
from aka.ingestion.indexer import build_index
from aka.ingestion.loader import load_documents
from aka.ingestion.manifest import read_manifest
from aka.ingestion.splitter import split_document
from aka.observability.feedback import record_feedback
from aka.pipeline.container import (
    build_chat_service,
    build_embedder,
    build_event_sink,
    embedding_model_id,
)
from aka.retrieval.vector_store import NumpyVectorStore

app = typer.Typer(help="AI Knowledge Assistant — citation-grounded SOP RAG.", no_args_is_help=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.command()
def build(
    root: str = typer.Option(".", help="Project root containing config/ and docs/."),
    force: bool = typer.Option(False, help="Rebuild even if inputs are unchanged."),
) -> None:
    """Ingest docs -> chunks -> embeddings -> index + manifest (incremental)."""
    settings = load_settings(root)
    embedder = build_embedder(settings)
    store = NumpyVectorStore(settings.resolve("paths.index_dir"))
    report = build_index(
        docs_dir=settings.resolve("paths.docs_dir"),
        index_dir=settings.resolve("paths.index_dir"),
        embedder=embedder,
        store=store,
        embedding_model_id=embedding_model_id(settings),
        timestamp=_now(),
        force=force,
    )
    if report.skipped:
        typer.echo(f"Index already up to date ({report.documents} docs). Use --force to rebuild.")
    else:
        typer.echo(f"Built index: {report.documents} docs -> {report.chunks} chunks.")


@app.command()
def validate(root: str = typer.Option(".", help="Project root.")) -> None:
    """Check that every referenced image resolves on disk."""
    settings = load_settings(root)
    docs_dir = settings.resolve("paths.docs_dir")
    missing = 0
    docs = load_documents(docs_dir)
    for doc in docs:
        for chunk in split_document(doc):
            base = Path(chunk.metadata.get("base_dir", "")) or docs_dir
            for img in chunk.images:
                if not (base / img.path).exists():
                    typer.echo(f"  MISSING image: {img.path}  (in {chunk.section_path})")
                    missing += 1
    if missing:
        typer.echo(f"\n{missing} missing image reference(s).")
        raise typer.Exit(code=1)
    typer.echo(f"OK — {len(docs)} document(s), all image references resolve.")


@app.command()
def stats(root: str = typer.Option(".", help="Project root.")) -> None:
    """Show knowledge-base statistics from the built index."""
    settings = load_settings(root)
    manifest = read_manifest(settings.resolve("paths.index_dir"))
    if not manifest:
        typer.echo("No index found. Run `aka build` first.")
        raise typer.Exit(code=1)
    typer.echo(f"Embedding model : {manifest.get('embedding_model')}")
    typer.echo(f"Documents       : {len(manifest.get('documents', {}))}")
    typer.echo(f"Chunks          : {manifest.get('chunk_count')}")
    typer.echo(f"Built at        : {manifest.get('built_at')}")


@app.command()
def chat(
    question: str = typer.Option(None, "--question", "-q", help="One-shot question; omit for REPL."),
    root: str = typer.Option(".", help="Project root."),
) -> None:
    """Ask a question (one-shot with -q, or interactive REPL)."""
    settings = load_settings(root)
    service = build_chat_service(settings)
    if question:
        _ask_and_print(service, question)
        return
    typer.echo("Knowledge Assistant. Ask a question (Ctrl-D / blank line to quit).")
    while True:
        try:
            q = input("\n> ").strip()
        except EOFError:
            break
        if not q:
            break
        _ask_and_print(service, q)


def _ask_and_print(service, question: str) -> None:
    result = service.ask(question)
    ctx = result.context
    answer = ctx.answer
    typer.echo(f"\n{answer.text if answer else '(no answer)'}")
    if answer and answer.citations:
        typer.echo("\nSources:")
        for c in answer.citations:
            figs = f"  [figures: {', '.join(i.path for i in c.images)}]" if c.images else ""
            typer.echo(f"  - {c.doc_title} :: {c.section_path}{figs}")
    if ctx.recommendations:
        typer.echo("\nRelated topics:")
        for r in ctx.recommendations:
            typer.echo(f"  - {r}")
    typer.echo(f"\n(interaction id: {result.interaction_id})")


@app.command()
def feedback(
    interaction_id: str = typer.Argument(..., help="Id printed after an answer."),
    rating: str = typer.Option(..., "--rating", help="yes | partial | no"),
    note: str = typer.Option("", "--note", help="Optional free-text comment."),
    root: str = typer.Option(".", help="Project root."),
) -> None:
    """Attach feedback to a prior interaction (append-only)."""
    settings = load_settings(root)
    sink = build_event_sink(settings)
    record_feedback(sink, interaction_id, rating=rating, note=note, timestamp=_now())
    typer.echo("Thanks — feedback recorded.")


@app.command()
def eval(root: str = typer.Option(".", help="Project root.")) -> None:
    """Run the golden-set evaluation (retrieval hit@k + groundedness)."""
    from aka.eval.runner import run_eval

    settings = load_settings(root)
    report = run_eval(settings)
    typer.echo(report.render())
    raise typer.Exit(code=0 if report.passed else 1)


if __name__ == "__main__":
    app()
