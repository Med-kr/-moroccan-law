#!/usr/bin/env python3
"""Re-apply the quality gate of the extended corpus to texts already built (after the gate
changed): failing texts are removed and added to data/corpus-excluded.json."""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

skill_dir = os.path.join(build.REPO, "skills", "maroc-corpus")
path = os.path.join(build.REPO, "data", "corpus-excluded.json")
excluded = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
removed = 0
# numbers of the text that neither other extractor reads (scripts/crosscheck.py maroc-corpus):
# a text with many of them has its figures garbled (tables of amounts run together)
xc_path = os.path.join(build.REPO, "data", "crosscheck-corpus.json")
xc = json.load(open(xc_path, encoding="utf-8")) if os.path.exists(xc_path) else {}
bad_numbers = {r["slug"]: r["numbers_in_neither_extractor"] for r in (xc.get("texts", []) if isinstance(xc, dict) else xc)}
for slug in sorted(os.listdir(os.path.join(skill_dir, "references"))):
    meta_p = os.path.join(skill_dir, "references", slug, "meta.json")
    if not os.path.exists(meta_p):
        continue
    info = json.load(open(meta_p, encoding="utf-8"))
    why = build.quality_gate(skill_dir, slug, info)
    if not why and bad_numbers.get(slug, 0) >= 20:
        why = f"figures garbled ({bad_numbers[slug]} numbers no other extractor reads, e.g. tables of amounts)"
    if why:
        shutil.rmtree(os.path.join(skill_dir, "references", slug))
        excluded.append({"slug": slug, "id": info["source_id"], "title": info["title"], "reason": why})
        removed += 1
        print(f"-- {slug}: {why}")
json.dump(excluded, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{removed} removed; {len(excluded)} excluded in total")
