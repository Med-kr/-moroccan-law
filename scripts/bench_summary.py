#!/usr/bin/env python3
"""Merge the JSON files written by `claude plugin eval --json` into one summary.

    python3 scripts/bench_summary.py --model "Claude Sonnet 5.5" evals/results/*.json

Writes evals/RESULTS.md and evals/results-summary.json. Only runs that completed
in both arms (with and without the plugin) are counted; nothing is estimated.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--model", required=True)
    args = ap.parse_args()
    cases = {f"cloze-{i:03d}": c for i, c in enumerate(json.load(open(os.path.join(REPO, "evals", "cases.json"), encoding="utf-8")), 1)}
    runs: dict[str, dict] = {}
    cost, started, version = 0.0, [], set()
    for path in args.files:
        r = json.load(open(path, encoding="utf-8"))
        if not r.get("cases"):
            continue
        cost += r.get("costUsd") or 0
        started.append(r["startedAt"][:10])
        version.add(r.get("claudeVersion"))
        for c in r["cases"]:
            a = c["arms"]
            if c["name"] in cases and a.get("with") and a.get("without") and not a["with"][0].get("error") \
                    and not a["without"][0].get("error"):
                runs.setdefault(c["name"], a)
    n = len(runs)
    if not n:
        print("no complete run found")
        return 1

    def passed(arm: str, name: str, grader: str | None) -> bool:
        g = {x["name"]: x["passed"] for x in runs[name][arm][0]["graders"]}
        return all(g.values()) if grader is None else g[grader]

    tot = {arm: {k: sum(passed(arm, c, g) for c in runs) for k, g in (("both", None), ("article", "article"), ("value", "value"))}
           for arm in ("with", "without")}
    by_skill: dict[str, list] = collections.defaultdict(lambda: [0, 0, 0])
    for c in runs:
        s = by_skill[cases[c]["skill"]]
        s[0] += 1
        s[1] += passed("with", c, None)
        s[2] += passed("without", c, None)
    no_tool = sum(1 for c in runs if runs[c]["with"][0]["turns"] <= 2 and not passed("with", c, None))
    summary = {"model": args.model, "claude_code": sorted(v for v in version if v), "dates": sorted(set(started)),
               "cases": n, "of": len(cases), "runs_per_case": 1, "cost_usd": round(cost, 2),
               "with_plugin": tot["with"], "without_plugin": tot["without"],
               "by_skill": {k: {"cases": v[0], "with": v[1], "without": v[2]} for k, v in sorted(by_skill.items())}}
    with open(os.path.join(REPO, "evals", "results-summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    pct = lambda x: f"{x}/{n} ({x / n:.0%})"
    md = [f"# Benchmark results", "",
          f"- Model: **{args.model}** (Claude Code {', '.join(summary['claude_code'])}), run on {', '.join(summary['dates'])}.",
          f"- {n} of {len(cases)} cases completed in both arms, 1 run per case, total cost ${cost:.2f}.",
          "- Task: fill in the figure removed from one sentence of a law and give the number of the article",
          "  (see `scripts/make_evals.py`; cases are generated from the texts with a fixed seed, graded by regular expressions).", "",
          "| | With the plugin | Without |", "|---|---|---|",
          f"| Figure **and** article number right | {pct(tot['with']['both'])} | {pct(tot['without']['both'])} |",
          f"| Figure right | {pct(tot['with']['value'])} | {pct(tot['without']['value'])} |",
          f"| Article number right | {pct(tot['with']['article'])} | {pct(tot['without']['article'])} |", "",
          "| Skill | Cases | Both right, with | Both right, without |", "|---|---|---|---|"]
    md += [f"| `{k}` | {v['cases']} | {v['with']} | {v['without']} |" for k, v in summary["by_skill"].items()]
    md += ["", "## What this does and does not show", "",
           "- It measures **finding and quoting the right provision**, which is what the plugin is for. It does not",
           "  measure legal reasoning, and a fill-in-the-blank question is easier to look up than a real client problem.",
           "- The ground truth is this project's own extraction of the official PDFs. An extraction error would be",
           "  scored as correct for the plugin arm. The extraction is checked separately (`scripts/crosscheck.py`).",
           "- One run per case: there is no estimate of run-to-run variance.",
           "- Texts that write figures in words only (most of the penal code, the family code) produce few cases,",
           "  so they are under-represented. Amending laws are excluded (two defensible article numbers).",
           f"- In {no_tool} of the plugin-arm misses the model answered in one or two turns without opening the skill.",
           "- Without the plugin the model had no access to the texts or to the web: the comparison is with the model's memory."]
    with open(os.path.join(REPO, "evals", "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
