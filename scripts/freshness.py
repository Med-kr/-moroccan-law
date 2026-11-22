#!/usr/bin/env python3
"""Is every amending law known to the catalog integrated in the bundled text?

For each bundled text (Arabic versions), finds the catalog entries whose title says they
amend, complete or repeal parts of that law ("بتغيير وتتميم القانون رقم 17.99", "modifiant
la loi n° 17-95"), and checks that the amending law's number appears in the bundled text
(consolidated texts cite every amending law in a footnote). An amending law missing from
the text means the consolidated version may predate it.

    python3 scripts/freshness.py            # report; exit 1 if something may be missing
Writes data/freshness.json. Standard library only.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUM = re.compile(r"(?<![\d.])(\d{1,3}\.\d{2})(?![\d.])")
AMEND = re.compile(r"بتغيير|بتتميم|بنسخ|يغير|يتمم|بتعديل|modifiant|complétant|abrogeant", re.I)


def own_numbers(slug: str, meta: dict) -> set[str]:
    nums = set(NUM.findall((meta.get("source_title", "") + " " + meta.get("title", "")).replace("-", ".")))
    m = re.search(r"(\d{1,3})-(\d{2})$", slug)
    if m:
        nums.add(f"{int(m.group(1))}.{m.group(2)}")
    return nums


def main() -> int:
    catalog = json.load(open(os.path.join(REPO, "data", "catalog.json"), encoding="utf-8"))["files"]
    amending = [f for f in catalog if AMEND.search(f.get("title") or "")]
    report, suspicious = [], 0
    for path in sorted(glob.glob(os.path.join(REPO, "skills", "*", "references", "*", "meta.json"))):
        slug = path.split(os.sep)[-2]
        meta = json.load(open(path, encoding="utf-8"))
        if meta.get("language") == "fr":
            continue
        own = own_numbers(slug, meta)
        if not own:
            continue
        text = open(os.path.join(os.path.dirname(path), "text.md"), encoding="utf-8").read().replace("-", ".")
        for f in amending:
            title = f["title"].replace("-", ".")
            if re.match(r"^\s*(مرسوم|قرار|مقرر|منشور|دورية|Décret|Arrêté|Circulaire)", title, re.I):
                continue                      # decrees amending decrees: not an amendment of the law
            nums = NUM.findall(title)
            # the law's own number must be what the title amends (« بتغيير وتتميم القانون رقم 17.99 »)
            if not any(re.search(rf"(?:{AMEND.pattern}).{{0,80}}(?:القانون|الظهير|loi|dahir)[^\d]{{0,25}}{re.escape(n)}",
                                 title, re.I) for n in own):
                continue
            others = [n for n in nums if n not in own]
            missing = [n for n in others if n not in text]
            row = {"text": slug, "amending_entry": f["title"], "adala_id": f.get("id"),
                   "amending_numbers": others, "not_cited_in_text": missing}
            report.append(row)
            if missing:
                suspicious += 1
                print(f"CHECK  {slug}: {', '.join(missing)} not cited — {f['title'][:110]}")
    with open(os.path.join(REPO, "data", "freshness.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"{len(report)} amending entries checked, {suspicious} possibly not integrated")
    return 1 if suspicious else 0


if __name__ == "__main__":
    sys.exit(main())
