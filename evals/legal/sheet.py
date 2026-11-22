#!/usr/bin/env python3
"""Write docs/LAWYER_REVIEW.md: the legal review set as a sheet a practitioner fills in."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
qs = json.load(open(os.path.join(HERE, "questions.json"), encoding="utf-8")) + \
    json.load(open(os.path.join(HERE, "holdout.json"), encoding="utf-8"))
out = ["# Review sheet for a practising lawyer / ورقة مراجعة لمحام ممارس / Fiche de relecture", "",
       "Ask Claude each question with the plugin installed, then grade the answer. The expected article",
       "is the one the program checks (`evals/legal/run.py`); the grade is the lawyer's: was the answer",
       "legally right, complete (exceptions, conditions, application in time) and safe to rely on?", "",
       "Grades: **A** right and complete · **B** right, something missing · **C** misleading · **D** wrong.", "",
       "| # | Domain | Question | Expected article | Grade | Comment |", "|---|---|---|---|---|---|"]
for q in qs:
    art = ", ".join(q["art"]) or "—"
    out.append(f"| {q['id']} | {q['skill'].replace('maroc-', '')} | {q['q']} | `{q['text']}` {art} |  |  |")
out += ["", "Reviewer: ________  Bar: ________  Date: ________", "",
        "Send the filled sheet as an issue or pull request; every C or D becomes a test."]
open(os.path.join(REPO, "docs", "LAWYER_REVIEW.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print(len(qs), "questions written to docs/LAWYER_REVIEW.md")
