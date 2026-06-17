# AI Knowledge Assistant (`aka`)

A citation-grounded **RAG prototype** for internal SOPs and tool usage — *not* a
general chatbot. It answers questions strictly from indexed documentation, always
cites its sources, refuses out-of-scope or unsupported questions instead of
guessing, suggests related topics, and logs every interaction for later analysis.

The demo corpus is a **fictional Acme Field App SOP** (Install → Authorization →
Select site → Checklist → Visit → Item detail → Finding) — a screenshot-anchored
procedural guide, which is why **images are first-class content** here. The sample
contains no real or internal data; point `docs_dir` at your own markdown to use it
for real (and keep that content out of the repo — see `.gitignore`).

## Design principle

> Freeze the architecture, not the features. Every new capability arrives as a new
> implementation behind a stable `Protocol`, or a new pipeline stage — never as an
> edit to the orchestration.

Three bounded contexts share only `domain/` (value objects) and `contracts/`
(Protocols). Modules never import each other; they communicate through `ChatContext`
during a request and through events afterward. Objects are constructed in exactly
one place: `aka.pipeline.container`.

```
question
  -> GuardStage        scope policy (thin; configurable regex)
  -> RetrievalStage    embed query -> nearest chunks (+ section path + images)
  -> GroundingStage    empty / low relevance -> escalate (primary anti-hallucination gate)
  -> GenerateStage     grounded answer + citations (answer ONLY from context)
  -> RecommendStage    related topics from a static graph
  -> InteractionLogged event -> append-only observability sink
```

### Anti-hallucination (no magic threshold)
1. **Grounded generation** — the model is instructed to answer only from retrieved
   passages, else emit a refusal sentinel.
2. **Mandatory citations** — assembled from the passages actually cited.
3. **Empty / low retrieval -> escalation** — a soft relevance floor + empty check,
   treated as a *weak signal*, never presented as calibrated confidence.

## Setup

```bash
uv sync                 # installs deps (incl. local embeddings; pulls torch)
export ANTHROPIC_API_KEY=sk-...   # for real generation
```

To run fully offline (no key, no model download) set `provider: fake` in
`config/embedding.yaml` and `config/llm.yaml`.

## Preprocess source documents (`.pdf` / `.pages` → markdown)

`aka build` ingests markdown. To turn raw SOPs into that markdown, use the optional
preprocessing pipeline (a per-material YAML profile is the only knob you tune):

```bash
uv sync --extra prep                      # pymupdf4llm + pillow (kept out of the core)
cp profiles/sample.yaml profiles/my-doc.yaml   # edit slug/title/structurer/headings/images
uv run aka prep path/to/MyDoc.pdf --profile profiles/my-doc.yaml
uv run aka prep-batch "inbox/*.pdf" --profile profiles/my-doc.yaml
```

This writes `docs/<slug>/sop.md` + `images/` (then run `aka build`). Notes:
- **`.pages`** is converted to PDF via **Apple Pages + AppleScript** — run on a Mac
  with Pages installed (or convert to PDF yourself, or use LibreOffice headless).
- **`structurer: deterministic`** (default) is free/offline; **`vision-llm`** has
  Claude read each page image and emit clean, figure-anchored markdown (set
  `ANTHROPIC_API_KEY`, best for screenshot-heavy SOPs).
- Markdown is the reviewable, hand-editable intermediate. Raw sources, profiles for
  internal material, and `var/prep/` intermediates are gitignored — nothing internal
  reaches the repo.

## Usage

```bash
uv run aka build                          # ingest docs/ -> index + manifest (incremental)
uv run aka validate                       # check every image reference resolves
uv run aka stats                          # KB statistics
uv run aka chat -q "How do I authorize the Acme Field app?"
uv run aka chat                           # interactive REPL
uv run aka feedback <interaction_id> --rating partial --note "..."
uv run aka eval                           # golden-set: retrieval hit@k + groundedness
uv run pytest                             # full pipeline, offline via fakes
```

## Configuration (`config/*.yaml`)

| File | Controls |
|------|----------|
| `app.yaml` | docs / index / events paths |
| `embedding.yaml` | embedding provider + model (`sentence-transformers` \| `fake`) |
| `retrieval.yaml` | `top_k`, `relevance_floor` |
| `llm.yaml` | generation provider + model (`anthropic` \| `fake`) |
| `policy.yaml` | guardrail deny patterns (regex) |
| `recommendation.yaml` | static topic graph |

No business logic is hardcoded — behaviour is tuned here.

## Swapping implementations

Everything behind a `Protocol` is replaceable with a one-line change in
`aka/pipeline/container.py`:

* Vector store: `NumpyVectorStore` → Chroma / FAISS
* LLM: `AnthropicLLM` → Ollama / other
* Embedder: `SentenceTransformerEmbedder` → a hosted embedding API
* Recommender: `StaticGraphRecommender` → analytics-derived edges

## Layout

```
src/aka/
  domain/         value objects (Document, Chunk, ImageRef, Citation, Answer, ChatContext, events)
  contracts/      Protocols (Embedder, VectorStore, Retriever, AnswerGenerator, Guardrail, Recommender, LLM, EventSink)
  ingestion/      OFFLINE: loader, heading-aware splitter, indexer, manifest
  retrieval/      embedders, NumPy vector store, retriever
  generation/     grounded prompt + answer generator
  guardrail/      config-driven scope policy
  recommendation/ static topic-graph recommender
  pipeline/       stages, runner, ChatService, container (DI)
  observability/  event sinks + feedback recorder
  llm/            Anthropic adapter + fake
  config/         typed settings loader
  cli/            typer entrypoints
  eval/           golden set + retrieval/groundedness runner
docs/sample-field-app/  fictional demo SOP markdown + placeholder images
```
