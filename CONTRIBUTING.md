# Contributing

## Add a legal text

1. Find it: `python3 skills/maroc-droit/scripts/catalog.py search <words or law number> --lang ar`.
   Prefer the Arabic consolidated version (title or file name containing «صيغة محينة»).
2. Add `{"id": <adala id>, "slug": "<short-latin-name>", "ar": "...", "fr": "..."}` to a skill in
   `countries/ma/skills.json`. Copy the law number from the official title; do not write it from memory.
3. `npm install`, then `uv run --with pymupdf python scripts/build.py --only <skill>`.
4. Read the result. Open `references/<slug>/text.md` next to the PDF and compare the first,
   the last and three articles in between. Check `meta.json`: `n_articles` should match the real
   size of the text and every line under `anomalies` should have an explanation.
5. `uv run --with pymupdf python scripts/crosscheck.py <skill>` and `uv run --with pymupdf python -m unittest discover -s tests`.
   After adding texts, `uv run --with pymupdf python scripts/glyph_table.py` refreshes the font reference table (`data/glyph-table.json`).

## Add a skill (new domain)

Add an entry to `countries/ma/skills.json` with `name` (prefix `maroc-`), `title_ar`, `title_fr`, `keywords`
(Arabic and French terms a lawyer would actually type) and its `texts`. `SKILL.md` is rendered
from `countries/ma/templates/SKILL.md.tmpl`; change the template, not the generated file.

## Fix an extraction error

Do not hand-edit files under `skills/*/references/`: they are regenerated. Fix `scripts/pdf_text.py`,
`scripts/extract.mjs` or `scripts/lawparse.py`, add a test in `tests/test_parser.py` that fails
before your change, and rebuild. If the official PDF itself contains the error, keep it as
published and mention it in the pull request.

## Rules

- Only official sources (Adala, Bulletin officiel). No commentary, no case-law summaries.
- French versions get the `-fr` suffix and `"lang": "fr"`, and keep the "may be out of date" label.
- A repealed text kept for comparison gets the `-mansukh` suffix and the "[منسوخ]" label.
- No claim in the README without a number produced by a script in this repository.
- The lookup tools stay standard-library Python, so the skills work with nothing to install.

## Add a country

The pipeline is not specific to Morocco. See [docs/ADDING_A_COUNTRY.md](docs/ADDING_A_COUNTRY.md).

## Benchmark

`python3 scripts/make_evals.py` regenerates the 100 fill-in-the-blank cases from the built texts
(fixed seed). Run them with
`claude plugin eval . --no-publish --runs 1 --allow-tools "Bash(python3:*)"`; it costs real
usage on your account. Do not edit the cases by hand, and report the model and the date with
any number you publish.
