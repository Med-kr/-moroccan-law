# Adding a country

The pipeline that built the Moroccan skills does not know anything about Morocco. A country is a
folder under `countries/` with three things: a description, a list of texts, and the wording of
the skills. Morocco (`countries/ma/`) is the reference implementation, and so far the only one.

```
countries/<code>/
├── country.json          who publishes the texts, languages, where the files below are
├── skills.json           the skills and the texts in each of them
└── templates/
    ├── SKILL.md.tmpl     instructions given to Claude for a domain skill
    └── ROUTER.md.tmpl    instructions for the general skill (catalog)
```

## 1. Find an official source

Use the texts published by the State (ministry of justice, official gazette, parliament), as PDF
with a text layer. Check that the publisher allows reuse, and write in `country.json` who
publishes them. Do not use commercial databases or a law firm's compilation.

## 2. List the texts

The quickest start needs no crawler: give each text a direct URL.

```json
{ "skills": [ {
    "name": "tunisie-civil", "title_ar": "...", "title_fr": "...", "keywords": "...",
    "texts": [ { "slug": "coc", "url": "https://.../code-obligations-contrats.pdf",
                 "ar": "مجلة الالتزامات والعقود", "fr": "Code des obligations et des contrats" } ]
} ] }
```

When the source has a browsable catalog, write an adapter in `sources/` that produces a
`catalog.json` (see `sources/adala.py`; the build only needs `files[]` with `id`, `locale`,
`title`, `url`, `path`, `updated_at`, `breadcrumbs`) and refer to texts by `id`. You then get the
weekly change detection (`build.py --check`) and the searchable catalog for free.

## 3. Build and look at the result

```bash
npm ci
uv run --with pymupdf python scripts/build.py --country <code>
```

The build prints, for each text, the number of articles and the anomalies it found. Open
`skills/<skill>/references/<text>/text.md` next to the PDF and check, at least:

- the number of articles against the known size of the text;
- a few articles at the start, in the middle and at the end, word for word;
- every line listed under `anomalies` in `meta.json`.

`scripts/crosscheck.py` compares the result with a second, independent extractor.

## 4. Language and numbering conventions

`scripts/lawparse.py` has two profiles, chosen automatically from the text:

| | Arabic | French |
|---|---|---|
| article heading | `المادة` / `الفصل` + number or ordinal | `Article` + number, `premier`, `bis`… |
| structure | الكتاب، القسم، الباب، الفرع… | Livre, Titre, Chapitre, Section… |
| version date | `صيغة محينة بتاريخ …` | `Version consolidée du …` |

Another language, or another way of numbering, is a new profile in that file plus tests in
`tests/test_parser.py`. Arabic PDFs have their own extraction problems (ligatures, right-to-left
order); `scripts/pdf_text.py` and `scripts/extract.mjs` document the ones solved so far.

## 5. Rules that do not change from one country to another

- Every text keeps its source URL, the checksum of the PDF and the date of the version.
- The skill instructions forbid quoting from memory and require the version date in every answer.
- What is not included (case law, implementing decrees, recent amendments) is written down.
- Law numbers in titles are copied from the official header, never typed from memory.
