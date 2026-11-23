#!/usr/bin/env python3
"""Arabic / French versions of the same text: articles present on one side only, and the
two version dates. Writes data/divergences-ar-fr.json. Standard library only."""
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import law  # noqa: E402

out = []
for fr_meta in sorted(glob.glob(os.path.join(REPO, "skills", "*", "references", "*-fr", "meta.json"))):
    law.ROOT = os.path.dirname(os.path.dirname(fr_meta))
    fr = fr_meta.split(os.sep)[-2]
    ar = fr[:-3]
    if ar not in law.texts():
        continue
    a = {law.canon(x["num"]) for x in law.load_articles(ar)}
    f = {law.canon(x["num"]) for x in law.load_articles(fr)}
    key = lambda n: [int(p) if p.isdigit() else 0 for p in n.replace(" ", "-").split("-")]
    out.append({"arabic": ar, "french": fr, "arabic_version": law.meta(ar).get("consolidated_on"),
                "french_version": law.meta(fr).get("consolidated_on"),
                "only_in_arabic": sorted(a - f, key=key), "only_in_french": sorted(f - a, key=key)})
json.dump(out, open(os.path.join(REPO, "data", "divergences-ar-fr.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for d in out:
    print(f"{d['arabic']:28} AR {d['arabic_version'] or '—':16} FR {d['french_version'] or '—':18} "
          f"only AR {len(d['only_in_arabic']):3}  only FR {len(d['only_in_french']):3}")
