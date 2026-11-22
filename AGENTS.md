# AGENTS.md

Instructions for AI agents (Codex, Gemini CLI, Cursor, Copilot, Claude Code, …) working in this
repository or answering questions with it.

## Answering a question on Moroccan law

Use the lookup tool of any skill folder; it is the same program everywhere (Python 3.10+, no dependency):

```bash
python3 skills/maroc-travail/scripts/law.py list                      # texts of a domain
python3 skills/maroc-corpus/scripts/law.py find التعليم المدرسي         # find a law by title or number (51.17)
python3 skills/maroc-procedure-civile/scripts/law.py search أجل الاستئناف --text msm-58-25
python3 skills/maroc-procedure-civile/scripts/law.py article msm-58-25 204 602
python3 skills/maroc-procedure-civile/scripts/law.py transitional msm-58-25
python3 skills/maroc-procedure-civile/scripts/delais.py calc --from 2026-11-03 --days 30
python3 skills/maroc-droit/scripts/catalog.py search مدونة السير          # 7,150 official documents
```

The domains are the folders `skills/maroc-*` (see `skills/<name>/SKILL.md` for the texts and the
method). Rules: never quote an article from memory; cite the law, the article and the Arabic
wording; give the version date and the official link printed by the tool; read `transitional`
when the facts may predate a reform; say when a text comes from `maroc-corpus` (automatic
extraction, not reviewed); there is no case law here, never invent a decision.

An MCP server exposes the same tools: `python3 mcp/server.py` (stdio) or `--http`; see
`docs/USE_WITH_ANY_AI.md`.

## Working on the code

- Build: `uv run --with pymupdf python scripts/build.py` (needs node with `npm ci`, and poppler-utils).
- Tests: `uv run --with pymupdf python -W ignore -m unittest discover -s tests` must pass.
- Checks before a release: `scripts/review_anomalies.py`, `scripts/freshness.py`,
  `evals/legal/run.py` and `--set holdout`, `scripts/crosscheck.py`.
- Never edit `skills/*/references/*` by hand: they are generated from the official PDFs. A
  correction of the source goes in `countries/ma/errata.json` (with its reason), a warning on an
  article in `countries/ma/article_notes.json`.
- Expected answers in `evals/legal/*.json` must come from the text of the article, not from memory.
