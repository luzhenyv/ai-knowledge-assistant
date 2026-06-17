---
name: document-preprocessing
description: >-
  Convert a source document — PDF, Apple Pages, Word (.docx), PowerPoint (.pptx),
  or loose page images — into the citation-ready markdown + images that the `aka`
  RAG ingestion consumes (docs/<slug>/sop.md + images/). Use when onboarding an
  SOP, manual, runbook, or tool-usage doc into the knowledge base. CLI-first via
  `aka prep`, with an agent-native vision fallback when extraction is poor.
---

# Document preprocessing

Turn one raw source document into the **ingestion contract** the knowledge base reads.
This is offline ETL upstream of `aka build`. Markdown is the human-reviewable,
version-controlled, hand-editable intermediate — get it right here and retrieval/citation
quality follows.

## 1. What you must produce (the contract)

Per document, write a folder under `docs/<slug>/`:

```
docs/<slug>/
  sop.md            # one `# H1` title, then `##` / `###` section headings
  images/           # screenshots referenced by sop.md
    p01-fig01.png
    ...
```

`sop.md` rules:
- Exactly one `# H1` (the document title) at the top.
- Real markdown headings (`##`, `###`) for every section — this is how the splitter
  chunks the doc, so a missing heading means a lost retrieval unit.
- Image references are **relative**: `![alt text](images/p01-fig01.png)`. Images are
  first-class — keep each screenshot in the section it illustrates.

The output is correct **only if it passes the contract check** (step 6). That check runs
the *real* ingestion code, so it's the same oracle the rest of the system uses.

## 2. Privacy guardrails — read first, non-negotiable

This repo is shared publicly; raw internal material must never reach git.
- **Never commit** raw sources (`*.pdf`, `*.docx`, `*.pptx`, `*.pages`) — already gitignored.
- **Never commit** generated internal docs: `docs/*` is gitignored except the synthetic
  `docs/sample-field-app`. Your `docs/<slug>/` output for real material stays private
  automatically — leave it that way.
- **Profiles for internal material stay private**: `profiles/*` is gitignored except
  `profiles/sample.yaml`. Name a real profile `profiles/<slug>.yaml` and do not force-add it.
- Conversion intermediates land in `var/prep/` (gitignored).
- Before any commit, confirm `git status` shows no raw source, no internal `docs/<slug>/`,
  no `var/`. If you ever need to share an example, build a **synthetic** one like the sample.

## 3. Pipeline overview

```
normalize -> extract -> structure -> place images -> emit -> VERIFY
   (to PDF)  (md+imgs)  (headings)   (filter+rename) (write)  (contract check)
```

`aka prep` performs extract → structure → place → emit for you. Your job per document is:
get the source to PDF, tune one small profile, run `aka prep`, review, and verify.

## 4. Procedure

### Step 0 — Classify the source
`.pdf` and `.pages` are handled directly by `aka prep`. Everything else
(`.docx/.pptx/.odt`, loose `.png/.jpg`) goes through the normalize front door first.

### Step 1 — Normalize to PDF

| Source | How |
|--------|-----|
| `.pdf` | Use as-is (pass straight to `aka prep`). |
| `.pages` | `aka prep` converts it via Apple Pages + AppleScript (run on a Mac with Pages). |
| `.docx` `.pptx` `.odt` `.ppt` `.doc` | `python scripts/normalize_to_pdf.py <file>` → LibreOffice headless. |
| one/many `.png` `.jpg` | `python scripts/normalize_to_pdf.py shot1.png shot2.png` → wrapped into one PDF (page order = arg order). |

`normalize_to_pdf.py` writes the PDF into `var/prep/pdf/` and prints its path. Feed that PDF
to `aka prep`. (`.pdf`/`.pages` don't need this script — `aka prep` takes them directly.)

### Step 2 — Write a profile (the one fine-tune knob)
Copy the sample and edit it for this material:

```bash
cp profiles/sample.yaml profiles/<slug>.yaml
```

Set `slug` (→ `docs/<slug>/`) and `title`. Pick a `structurer`:
- `deterministic` (default) — free/offline; good when the PDF has selectable text.
- `vision-llm` — Claude reads each page image and emits clean, figure-anchored markdown;
  best for **screenshot-heavy** SOPs or scanned/low-text PDFs. Needs `ANTHROPIC_API_KEY`.

Tune `headings` regexes so numbered SOP headings become real markdown levels, `images`
min sizes to drop icons/bullets, and `pages` to a range if you only want part of the doc.
See the knob table in §5.

### Step 3 — Run the preprocessor
```bash
uv sync --extra prep                         # once: pymupdf4llm + pillow
uv run aka prep <pdf-or-.pages> --profile profiles/<slug>.yaml
# many files sharing one profile (slug derives from each filename):
uv run aka prep-batch "inbox/*.pdf" --profile profiles/<slug>.yaml
```
This writes `docs/<slug>/sop.md` + `images/` and prints a report (pages, headings found,
images kept/dropped).

### Step 4 — Review and tune
Open `docs/<slug>/sop.md` and check:
- One `# H1`, and every section has a `##`/`###` heading (report warns if **0** headings —
  almost always means the `headings` regexes need adjusting).
- Figures sit in the right section; junk icons were dropped (raise `images.min_width/height`
  if not).
- Page numbers / repeated footers were stripped.

Adjust the profile and re-run. **Decision rule:** if deterministic output is messy, or the
pages are mostly screenshots with little selectable text, switch `structurer: vision-llm`
and re-run.

### Step 5 — Agent-native fallback (no CLI, or extraction still poor)
When `aka`/its deps aren't installed, or both structurers produce bad markdown, do the ETL
yourself — the same way the `docs/sample-field-app` example was originally authored:
1. Get page images: `python scripts/normalize_to_pdf.py <source>` to get a PDF, then
   rasterize pages to PNG (any tool, e.g. `pdftoppm`, Preview export, or PyMuPDF
   `page.get_pixmap`).
2. **Read each page image** and write `docs/<slug>/sop.md` by hand to the §1 contract:
   one H1, a `##` per section, prose that faithfully reflects the page.
3. Copy the relevant screenshots into `docs/<slug>/images/` with stable names
   (`p01-fig01.png`) and reference them inline where they belong.
Do not invent content that isn't in the source. This path is not reproducible, so prefer
the CLI when it works.

### Step 6 — Verify (always)
```bash
python .claude/skills/document-preprocessing/scripts/check_contract.py docs/<slug>
uv run aka build        # ingest docs/ -> index (incremental)
uv run aka validate     # every image reference resolves on disk
```
`check_contract.py` runs the real ingestion (`load_documents` + `split_document`) and fails
loudly if the H1, headings, or image refs are wrong — fix `sop.md`/the profile until it passes
*before* `aka build`.

## 5. Profile knobs (`profiles/<slug>.yaml`)

| Key | Meaning | Default |
|-----|---------|---------|
| `slug` | output dir `docs/<slug>/` | — (required) |
| `title` | document H1; inferred if omitted | `null` |
| `source_type` | `auto` \| `pdf` \| `pages` | `auto` |
| `extractor` | extraction engine | `pymupdf4llm` |
| `structurer` | `deterministic` \| `vision-llm` | `deterministic` |
| `pages` | `all` or a range like `2-14` | `all` |
| `images.min_width` / `min_height` | drop images smaller than this (icons/rules) | `80` / `80` |
| `images.keep_formats` | image formats to keep | `[png, jpeg, jpg]` |
| `headings[].pattern` / `level` | regex → markdown heading level coercion | `[]` |
| `llm.model` / `dpi` / `prompt_profile` | vision-llm settings only | `claude-sonnet-4-6` / `150` / `sop` |

Heading examples: `{ pattern: '^\d+\.?\s+\S', level: 2 }` turns `1. Install` into `## 1. Install`;
`{ pattern: '^\d+\.\d+\s+\S', level: 3 }` turns `1.2 Sign in` into `### 1.2 Sign in`.

## 6. Helper scripts (this skill's `scripts/`)

- `normalize_to_pdf.py <src...> [--out var/prep/pdf]` — best-effort source→PDF front door:
  `.pdf` passthrough, Office formats via LibreOffice (`soffice --headless`), `.pages` via
  Apple Pages, loose images combined into one PDF via Pillow. Prints the PDF path.
- `check_contract.py <docs/<slug>|docs/>` — runs the real ingestion over the output and
  asserts the §1 contract (H1 present, ≥1 heading, every image ref resolves). Exits non-zero
  on failure. The acceptance oracle for both the CLI and hand-authored paths.

## 7. Portability

This skill is plain markdown plus two stdlib+Pillow scripts — no Claude-Code-only features.
Any agent (Claude Code, opencode, …) or a human can follow it. The CLI path is reproducible;
the agent-native fallback (§4, step 5) is the escape hatch when tooling is unavailable.
