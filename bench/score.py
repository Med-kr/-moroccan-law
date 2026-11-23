#!/usr/bin/env python3
"""Score a benchmark run on the five measures and write the public results.

    python3 bench/score.py bench/results-<run>.json

Reads the final answer of every run from its trace (run with --keep-temp), then:
  retrieval      the expected article is given on the « المادة: » line (regex grader)
  citation       the passage on the « النص: » line exists word for word in the official text
                 (diacritics, hamza seats and punctuation ignored; at least 6 words)
  currentness    the « الحالة: » line reports the repeal or the amendment (regex grader)
  hallucination  no invented article, law or court decision: the answer says it does not exist /
                 is not available, and gives no decision number
  reasoning      the computed figure is in the answer (regex grader)
Writes bench/answers.jsonl (every final answer, for anyone to check) and bench/summary.json.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))
import law  # noqa: E402

DECISION = re.compile(r"(?:قرار|القرار)\s*(?:عدد|رقم)\s*:?\s*\d+|arr[êe]t\s*(?:n°|no|numéro)\s*\d+|\b\d{2,5}\s*/\s*\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4}\b", re.I)
REFUSAL = re.compile(r"غير موجود|لا يوجد|لا توجد|لم أجد|لا أجد|لا تتضمن|لا أتوفر|ليس لدي|لا أملك|لا يمكنني|n'existe|introuvable|aucune loi|ne dispose|pas accès|ne peux pas|n'ai pas", re.I)


def final_text(trace):
    if not trace or not os.path.exists(trace):
        return ""
    last = ""
    for line in open(trace, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            txt = "".join(c.get("text", "") for c in ev["message"].get("content", []) if c.get("type") == "text")
            if txt.strip():
                last = txt
    return last


def flat(s):
    s = law.norm(s)
    s = re.sub(r"\[\^\d+\]", " ", s)
    return " ".join(re.findall(r"[^\W_]+", s))


_texts = {}


def text_of(skill, slug):
    if (skill, slug) not in _texts:
        law.ROOT = os.path.join(REPO, "skills", skill, "references")
        _texts[(skill, slug)] = flat(" ".join(a["body"] for a in law.load_articles(slug)))
    return _texts[(skill, slug)]


def citation_ok(answer, skill, slug):
    m = re.search(r"النص\**\s*[:：]\s*\**\s*«([^»]{10,})»", answer)
    if not m:
        return False
    quote = flat(m.group(1).replace("…", " ").replace("...", " "))
    parts = [p.strip() for p in re.split(r"\s{2,}", quote) if p.strip()]
    words = quote.split()
    return len(words) >= 6 and quote in text_of(skill, slug)


def main(path):
    run = json.load(open(path, encoding="utf-8"))
    meta = {c["id"]: c for c in json.load(open(os.path.join(HERE, "cases.json"), encoding="utf-8"))}
    rows, out = [], open(os.path.join(HERE, "answers.jsonl"), "w", encoding="utf-8")
    invalid = 0
    for case in run["cases"]:
        m = meta.get(case["name"])
        if not m:
            continue
        for arm in ("with", "without"):
            for r in case["arms"].get(arm, []):
                ans = final_text(r.get("tracePath"))
                if not ans.strip() or re.search(r"hit your .{0,20}limit|usage limit|rate limit", ans, re.I):
                    invalid += 1             # the run never reached the model: not a failure, not scored
                    continue
                g = {x["name"]: x["passed"] for x in r["graders"]}
                row = {"id": m["id"], "category": m["category"], "arm": arm, "cost": r["costUsd"], "turns": r["turns"]}
                if m["category"] == "retrieval":
                    row["retrieval"] = g.get("article", False)
                    row["citation"] = citation_ok(ans, m["skill"], m["text"])
                elif m["category"] == "currentness":
                    row["currentness"] = g.get("status", False)
                elif m["category"] == "hallucination":
                    no_invention = not DECISION.search(ans) if "decision" in m.get("trap", "") else True
                    row["hallucination_free"] = bool(no_invention and (g.get("absent") or g.get("no-decision") or REFUSAL.search(ans)))
                elif m["category"] == "reasoning":
                    row["reasoning"] = g.get("result", False)
                    row["retrieval"] = g.get("article", False)
                rows.append(row)
                out.write(json.dumps({**row, "question": m["question"], "answer": ans}, ensure_ascii=False) + "\n")
    out.close()
    summary = {"run": os.path.basename(path), "model": run["suite"].get("modelOverride"), "date": run["startedAt"][:10],
               "cost_usd": round(run["costUsd"], 2), "partial": run.get("partial", False),
               "runs_not_scored": invalid, "measures": {}}
    for measure in ("retrieval", "citation", "currentness", "hallucination_free", "reasoning"):
        for arm in ("with", "without"):
            vals = [r[measure] for r in rows if r["arm"] == arm and measure in r]
            if vals:
                summary["measures"].setdefault(measure, {})[arm] = {"passed": sum(vals), "total": len(vals)}
    json.dump(summary, open(os.path.join(HERE, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in summary["measures"].items():
        w, wo = v.get("with", {}), v.get("without", {})
        print(f"{k:20} with {w.get('passed')}/{w.get('total')}   without {wo.get('passed')}/{wo.get('total')}")
    print("cost", summary["cost_usd"], "partial", summary["partial"], "runs not scored (no answer / usage limit)", invalid)


if __name__ == "__main__":
    main(sys.argv[1])
