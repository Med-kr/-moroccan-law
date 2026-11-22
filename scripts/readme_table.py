#!/usr/bin/env python3
"""Rewrite the skills table of the three READMEs from the built skills (titles, article counts)."""
import glob
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(REPO, "countries", "ma", "skills.json"), encoding="utf-8"))


def rows(lang: str) -> list[str]:
    out = []
    for sk in cfg["skills"]:
        cur, old, fr = [], [], 0
        for t in sk["texts"]:
            mp = glob.glob(os.path.join(REPO, "skills", sk["name"], "references", t["slug"], "meta.json"))
            if not mp:
                continue
            m = json.load(open(mp[0], encoding="utf-8"))
            if m.get("language") == "fr":
                fr += 1
                continue
            title = t["ar"] if lang == "ar" else t["fr"]
            (old if t.get("repealed") or "mansukh" in t["slug"] else cur).append(f"{title} ({m['n_articles']})")
        dom = sk["title_ar"] if lang == "ar" else sk["title_fr"]
        if sk.get("auto"):
            ms = [json.load(open(m, encoding="utf-8")) for m in
                  glob.glob(os.path.join(REPO, "skills", sk["name"], "references", "*", "meta.json"))]
            n, arts = len(ms), sum(m["n_articles"] for m in ms)
            cell = {"en": f"{n} laws and dahirs ({arts:,} articles), automatic extraction behind quality gates; find them with `law.py find`",
                    "fr": f"{n} lois et dahirs ({arts:,} articles), extraction automatique contrôlée ; les trouver avec `law.py find`",
                    "ar": f"{n} قانونا وظهيرا ({arts:,} مادة)، استخراج آلي بمراقبة آلية؛ البحث عنها بـ `law.py find`"}[lang]
            out.append(f"| `{sk['name']}` | {dom} | {cell} | — |")
            continue
        cell = "; ".join(cur)
        if old:
            cell += {"ar": "<br>*منسوخة، للمقارنة:* ", "fr": "<br>*Abrogés, pour comparaison :* ",
                     "en": "<br>*Repealed, for comparison:* "}[lang] + "; ".join(old)
        out.append(f"| `{sk['name']}` | {dom} | {cell} | {fr or '—'} |")
    return out


for lang, name in (("en", "README.md"), ("fr", "README.fr.md"), ("ar", "README.ar.md")):
    p = os.path.join(REPO, name)
    s = open(p, encoding="utf-8").read()
    new = "\n".join(rows(lang)) + "\n"
    s2, n = re.subn(r"(\|---\|---\|---\|---\|\n)(?:\| `maroc-[^\n]*\n)+", lambda m: m.group(1) + new, s, count=1)
    assert n == 1, name
    open(p, "w", encoding="utf-8").write(s2)
    print(name, len(new.splitlines()), "rows")
