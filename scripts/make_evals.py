#!/usr/bin/env python3
"""Generate the citation benchmark (evals/) from the built texts.

Each case is a fill-in-the-blank question taken from one article: a sentence
that contains exactly one figure written as "word (N) unit" has the figure
removed, and the model must give the figure and the number of the article.
Both answers are checked with a regular expression, so no judge model and no
opinion are involved. The same cases run with and without the plugin:

    claude plugin eval . --no-publish --runs 1 --allow-tools "Bash(python3:*)"

The selection is deterministic (fixed seed): the questions are not hand-picked.

    python3 scripts/make_evals.py [--n 100] [--seed 2026]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import law  # noqa: E402

UNIT = r"(?:يوما|يوم|أيام|شهرا|شهر|أشهر|سنة|سنوات|ساعة|درهم|عضوا|أعضاء|بالمائة|في المائة)"
FIG = re.compile(rf"(?:\((\d+)\)|(?<![\d.])(\d+))\s*({UNIT})(?![\u0621-\u064A])")
NUMWORD = re.compile(r"^و?(?:ال)?(?:واحد|واحدة|إحدى|أحد|اثن\w*|إثن\w*|ثلاث\w*|أربع\w*|خمس\w*|ست|ستة|ستين|ستون|سبع\w*|ثمان\w*|تسع\w*|"
                     r"عشر\w*|مائة|مئة|مائتي\w*|مائتا\w*|ألف|ألفي\w*|آلاف|مليون\w*)$")


def candidates(skill: str, slug: str) -> list[dict]:
    law.ROOT = os.path.join(REPO, "skills", skill, "references")
    m = law.meta(slug)
    out = []
    for a in law.load_articles(slug):
        if not re.fullmatch(r"\d+(?:[-.]\d+)?", a["num"]):
            continue
        body = re.sub(r"^\[\^\d+\]:.*$", "", a["body"], flags=re.M)
        for sent in re.split(r"(?<=[.؛])\s+|\n+", body):
            sent = re.sub(r"\[\^\d+\]", "", sent).strip()
            figs = list(FIG.finditer(sent))
            if len(figs) != 1 or not 70 <= len(sent) <= 260 or len(re.findall(r"\d+", sent)) != 1:
                continue
            f = figs[0]
            value, unit = f.group(1) or f.group(2), f.group(3)
            before = sent[:f.start()].split()
            while before and NUMWORD.match(before[-1]):      # the words that spell the number go too
                before.pop()
            blank = " ".join(before + ["____", unit]) + sent[f.end():]
            if len(before) < 4:
                continue
            out.append({"skill": skill, "slug": slug, "title": m["title"], "kw": m["article_keyword"],
                        "num": a["num"], "value": value, "unit": unit, "sentence": sent, "blank": blank})
            break
    return out


# Laws that mostly insert articles into other codes: a sentence found there has two defensible
# article numbers (the amending article and the inserted one), so they give no clean ground truth.
AMENDING = {"oqubat-badila", "tabadul-53-05"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    config = json.load(open(os.path.join(REPO, "countries", "ma", "skills.json"), encoding="utf-8"))
    pools = []
    for s in config["skills"]:
        for t in s["texts"]:
            if t.get("lang") == "fr" or "mansukh" in t["slug"] or t["slug"] in AMENDING:
                continue
            c = candidates(s["name"], t["slug"])
            if c:
                pools.append(c)
    rng = random.Random(args.seed)
    for p in pools:
        rng.shuffle(p)
    picked: list[dict] = []
    # round-robin over the texts so that no single code dominates
    while len(picked) < args.n and any(pools):
        for p in pools:
            if p and len(picked) < args.n:
                picked.append(p.pop())
    out_dir = os.path.join(REPO, "evals")
    for d in os.listdir(out_dir) if os.path.isdir(out_dir) else []:
        if d.startswith("cloze-"):
            shutil.rmtree(os.path.join(out_dir, d))
    for i, c in enumerate(picked, 1):
        d = os.path.join(out_dir, f"cloze-{i:03d}")
        os.makedirs(os.path.join(d, "graders"), exist_ok=True)
        with open(os.path.join(d, "prompt.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nmax_turns: 12\nallowed_tools: [Read, Glob, Grep, Skill, Bash]\n---\n\n"
                     f"سؤال في القانون المغربي. في «{c['title']}»، أكمل الفراغ في المقتضى التالي "
                     f"واذكر رقم ({c['kw']}) الذي ورد فيه هذا المقتضى:\n\n«{c['blank']}»\n\n"
                     "أنه جوابك بهذين السطرين بالضبط، بالأرقام:\n"
                     f"القيمة: <العدد>\n{c['kw']}: <الرقم>\n")
        num = re.escape(c["num"]).replace(r"\-", "[-.]").replace(r"\.", "[-.]")
        with open(os.path.join(d, "graders", "value.md"), "w", encoding="utf-8") as fh:
            fh.write(f"---\ntype: regex\nname: value\ntarget: last_message\nweight: 1\n---\n\n"
                     f"القيمة\\**\\s*[:：]\\s*\\**\\s*{c['value']}(?!\\d)\n")
        with open(os.path.join(d, "graders", "article.md"), "w", encoding="utf-8") as fh:
            fh.write(f"---\ntype: regex\nname: article\ntarget: last_message\nweight: 1\n---\n\n"
                     f"{c['kw']}\\**\\s*[:：]\\s*\\**\\s*{num}(?![\\d.-])\n")
    with open(os.path.join(out_dir, "cases.json"), "w", encoding="utf-8") as fh:
        json.dump([{k: c[k] for k in ("skill", "slug", "num", "value", "unit", "sentence")} for c in picked],
                  fh, ensure_ascii=False, indent=1)
    by = {}
    for c in picked:
        by[c["skill"]] = by.get(c["skill"], 0) + 1
    print(f"{len(picked)} cases from {len(pools)} texts -> evals/")
    print(", ".join(f"{k} {v}" for k, v in sorted(by.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
