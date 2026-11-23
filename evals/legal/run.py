#!/usr/bin/env python3
"""Legal review set: 40 questions a practitioner asks, in darija, French and Arabic,
with the article that answers each one and the words of the answer that must be in it.

Two checks, no model and no cost:
  gold      the expected article exists and says what the expected answer says
            (guards the set itself against answers written from memory);
  retrieval the search a careful user would type finds that article in the first
            results (what Claude does with the skill before answering).

    python3 evals/legal/run.py [--top 5] [--set holdout]
questions.json and holdout.json were used while improving the search. holdout2.json (40
questions, written before the second round of changes and measured once after it) is the honest
score: top 5 31 -> 31 / 40, first result 22 -> 23 / 40, i.e. no real gain from the
second round: lexical search is at its ceiling on these texts; semantic search is the next step.
Results in evals/legal/results.json. The questions can also be put to a lawyer as a review
sheet (docs/LAWYER_REVIEW.md).
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def law(q, *args):
    p = subprocess.run([sys.executable, os.path.join(REPO, "skills", q["skill"], "scripts", "law.py"), *args],
                       capture_output=True, text=True)
    return p.stdout


def main() -> int:
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 5
    name = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "questions"
    qs = json.load(open(os.path.join(HERE, name + ".json"), encoding="utf-8"))
    rows, gold_ok, found = [], 0, 0
    for q in qs:
        body = law(q, "article", q["text"], *q["art"])
        g = bool(q["art"]) and all(m in body for m in q["must"])
        out = law(q, "search", *q["search"], "--text", q["text"], "--max", str(top))
        hits = re.findall(r"^- \S+ ([^\s:]+)", out, re.M)
        r = any(h in q["art"] for h in hits[:top])
        gold_ok += g
        found += r
        rows.append({"id": q["id"], "gold": g, "retrieved": r, "hits": hits[:top]})
        print(f"{q['id']:4} gold {'ok ' if g else 'BAD'}  retrieval {'ok ' if r else 'MISS'}  {q['art']} <- {hits[:top]}")
    n = len(qs)
    summary = {"questions": n, "gold_ok": gold_ok, "retrieved_top": found, "top": top}
    json.dump({"summary": summary, "rows": rows}, open(os.path.join(HERE, ("results" if name == "questions" else "results-" + name) + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\ngold {gold_ok}/{n}   retrieval in top {top}: {found}/{n}")
    return 0 if gold_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
