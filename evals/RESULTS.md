# Benchmark results

- Model: **Claude Sonnet 5.5** (Claude Code 2.1.328), run on 2026-11-19.
- 100 of 100 cases completed in both arms, 1 run per case, total cost $13.94.
- Task: fill in the figure removed from one sentence of a law and give the number of the article
  (see `scripts/make_evals.py`; cases are generated from the texts with a fixed seed, graded by regular expressions).

| | With the plugin | Without |
|---|---|---|
| Figure **and** article number right | 95/100 (95%) | 7/100 (7%) |
| Figure right | 100/100 (100%) | 48/100 (48%) |
| Article number right | 95/100 (95%) | 9/100 (9%) |

| Skill | Cases | Both right, with | Both right, without |
|---|---|---|---|
| `maroc-administratif` | 14 | 13 | 0 |
| `maroc-assurances-banques` | 8 | 8 | 2 |
| `maroc-civil` | 8 | 8 | 1 |
| `maroc-commerce` | 11 | 10 | 1 |
| `maroc-fiscal-douane` | 6 | 5 | 0 |
| `maroc-immobilier` | 4 | 4 | 1 |
| `maroc-libertes-publiques` | 7 | 6 | 1 |
| `maroc-numerique` | 6 | 6 | 1 |
| `maroc-penal` | 2 | 2 | 0 |
| `maroc-procedure-civile` | 4 | 4 | 0 |
| `maroc-procedure-penale` | 4 | 4 | 0 |
| `maroc-professions-judiciaires` | 15 | 15 | 0 |
| `maroc-propriete-intellectuelle` | 4 | 3 | 0 |
| `maroc-travail` | 7 | 7 | 0 |

## What this does and does not show

- It measures **finding and quoting the right provision**, which is what the plugin is for. It does not
  measure legal reasoning, and a fill-in-the-blank question is easier to look up than a real client problem.
- The ground truth is this project's own extraction of the official PDFs. An extraction error would be
  scored as correct for the plugin arm. The extraction is checked separately (`scripts/crosscheck.py`).
- One run per case: there is no estimate of run-to-run variance.
- Texts that write figures in words only (most of the penal code, the family code) produce few cases,
  so they are under-represented. Amending laws are excluded (two defensible article numbers).
- In 2 of the plugin-arm misses the model answered in one or two turns without opening the skill.
- Without the plugin the model had no access to the texts or to the web: the comparison is with the model's memory.

## Notes on this run

- The cases in `evals/` are the ones that were run. `scripts/make_evals.py` regenerates cases from
  the current texts, so after a rebuild that changes a text the selection can differ.
- Three cases (024, 057, 085) come from law 55-19, whose text at the time still carried a font
  defect of the source PDF (a stray "ه" between some words). The defect was repaired after the
  run; the figures and article numbers of these cases were not affected.
- The texts were rebuilt after the run with further corrections (font tables, footnotes, section
  titles). 97 of the 100 cases read exactly the same in the rebuilt texts; the other three are the
  cases of law 55-19 above.
