#!/usr/bin/env python3
"""Build data/glyph-table.json: for each embedded font, which text each glyph stands for.

The source PDFs embed the same few fonts (Times New Roman, Arial...) with the original glyph
numbers, each with its own glyph -> text map written by Word. A given file sometimes has a
wrong entry; the same glyph in the other files does not. This script reads the maps of every
PDF in .cache/pdf, lets them vote, and keeps the entries a clear majority agrees on.
scripts/pdf_text.py uses the table to correct the odd one out.

    uv run --with pymupdf python scripts/glyph_table.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pdf_text  # noqa: E402

MIN_FONTS = 5       # a glyph must be seen in at least this many files
MIN_SHARE = 0.8     # ... and this share of them must agree


def main() -> int:
    votes: dict[tuple[str, int], collections.Counter] = collections.defaultdict(collections.Counter)
    files = sorted(glob.glob(os.path.join(REPO, ".cache", "pdf", "*.pdf")))
    for path in files:
        doc = pymupdf.open(path)
        pdf_text.patch_cmaps(doc, use_table=False)
        seen = set()
        per_file: dict[tuple[str, int], str] = {}
        for name, xref in pdf_text.type0_fonts(doc):
            if xref in seen:
                continue
            seen.add(xref)
            for g, u in pdf_text.parse_cmap(doc.xref_stream(xref).decode("latin-1")).items():
                per_file.setdefault((name, g), u)          # one vote per file
        for key, u in per_file.items():
            votes[key][u] += 1
    fonts: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for (name, g), c in sorted(votes.items()):
        top, n = c.most_common(1)[0]
        total = sum(c.values())
        if total >= MIN_FONTS and n / total >= MIN_SHARE and pdf_text._has_arabic(top):
            fonts[name][f"{g:04X}"] = top
    with open(pdf_text.GLYPH_TABLE_PATH, "w", encoding="utf-8") as fh:
        json.dump({"files": len(files), "min_fonts": MIN_FONTS, "min_share": MIN_SHARE, "fonts": fonts},
                  fh, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"{len(files)} PDFs, {sum(len(t) for t in fonts.values())} glyphs in {len(fonts)} fonts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
