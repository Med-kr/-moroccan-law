#!/usr/bin/env python3
"""Cross-check the bundled text of each law against two other extractors.

The build uses pdf.js. Here the same (CMap-repaired) PDF is read with poppler's
pdftotext and with MuPDF, and three things are compared:

- words: a word of the bundled text found in neither other extraction is a candidate
  extraction error (glued, split or mis-ordered letters);
- numbers: every figure of the bundled text (time limits, amounts, article and law
  numbers) must exist, as written, in one of the other extractions;
- missing text: words both other extractions have more often than the bundled text
  (text dropped on the way).

What this cannot see: a wrong letter that all three extractors read from the same faulty
font table. That is covered separately by the glyph table (scripts/glyph_table.py).

    uv run --with pymupdf python scripts/crosscheck.py [skill ...]

Writes data/crosscheck.json (reviewed skills) or data/crosscheck-corpus.json
(`crosscheck.py maroc-corpus`, the extended corpus) and prints one line per text.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pdf_text  # noqa: E402

DIACRITICS = dict.fromkeys(list(range(0x064B, 0x0653)) + [0x0670])   # harakat split words for the tokenizer
WORD = re.compile(r"[ء-ي]{3,}|[A-Za-zÀ-ÿ]{3,}")     # Arabic words, and Latin ones for the French versions


def words(text: str) -> collections.Counter:
    text = text.translate(pdf_text.BIDI_CTRL).translate(pdf_text.GLYPH_FIX).translate(DIACRITICS)
    return collections.Counter(WORD.findall(text))


def bigrams(text: str) -> collections.Counter:
    """Adjacent pairs of Arabic words: sensitive to word ORDER, not just vocabulary."""
    text = text.translate(pdf_text.BIDI_CTRL).translate(pdf_text.GLYPH_FIX).translate(DIACRITICS)
    out: collections.Counter = collections.Counter()
    for para in re.split(r"\n\s*\n|\f", text):
        w = WORD.findall(para)
        out.update(zip(w, w[1:]))
    return out


NUMBER = re.compile(r"\d+(?:[.,/]\d+)*")


def numbers(text: str, own: bool = False) -> collections.Counter:
    text = text.translate(pdf_text.BIDI_CTRL)
    if own:                                  # footnote marks are this project's notation
        text = re.sub(r"^\[\^\d+\]:", " ", text, flags=re.M)
        text = re.sub(r"\[\^\d+\]", " ", text)
    return collections.Counter(NUMBER.findall(text))


def other_texts(pdf: str) -> tuple[str, str]:
    """(poppler text, MuPDF text) of the CMap-repaired file."""
    doc = pymupdf.open(pdf)
    pdf_text.patch_cmaps(doc)
    mu = "\n".join(page.get_text() for page in doc)
    with tempfile.TemporaryDirectory() as tmp:
        fixed = os.path.join(tmp, "f.pdf")
        doc.save(fixed)
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", fixed, "-"], capture_output=True, check=True).stdout
    return out.decode("utf-8", "replace"), mu


def poppler_text(pdf: str) -> str:
    return other_texts(pdf)[0]


def main() -> int:
    only = set(sys.argv[1:])
    results = []
    worst = 0.0
    for meta_path in sorted(glob.glob(os.path.join(REPO, "skills", "*", "references", "*", "meta.json"))):
        skill = meta_path.split(os.sep)[-4]
        if (only and skill not in only) or (not only and skill == "maroc-corpus"):
            continue        # the extended corpus is checked on its own: crosscheck.py maroc-corpus
        meta = json.load(open(meta_path, encoding="utf-8"))
        cached = glob.glob(os.path.join(REPO, ".cache", "pdf", f"{meta['source_id']}-*.pdf"))
        if not cached:
            print(f"-- {skill}/{meta['slug']}: PDF not in cache, run build first")
            continue
        with open(os.path.join(os.path.dirname(meta_path), "text.md"), encoding="utf-8") as fh:
            whole = fh.read()
        # skip the lines this project adds (titles, source banner, section paths)
        mine = "".join(l if not l.startswith(("#", ">")) else "\n" for l in whole.splitlines(True))
        everything = words(whole)      # headings included: they are text of the source too
        ours = words(mine)
        second, third = other_texts(cached[0])
        ref = words(second)
        ref3 = words(third)
        my_nums = numbers(mine, own=True)
        n2, n3 = numbers(second), numbers(third)
        odd_nums = {k: c for k, c in my_nums.items() if not n2[k] and not n3[k]}
        dropped = {w: min(ref[w], ref3[w]) - everything[w] for w in ref if w in ref3 and min(ref[w], ref3[w]) > everything[w]}
        # word order: pairs of ours that the second extractor never has side by side.
        # poppler keeps the PDF's line breaks, so join its lines before pairing.
        ref_pairs = bigrams(re.sub(r"(?<!\n)\n(?!\n)", " ", second))
        my_pairs = bigrams(mine)
        n_pairs = sum(my_pairs.values())
        bad_pairs = sum(c for pair, c in my_pairs.items() if pair not in ref_pairs)
        total = sum(ours.values())
        unknown = {w: c for w, c in ours.items() if w not in ref}
        n_unknown = sum(unknown.values())
        neither = {w: c for w, c in unknown.items() if w not in ref3}
        missing = sum(c for w, c in ref.items() if w not in ours)
        rate = n_unknown / total if total else 0.0
        worst = max(worst, rate)
        results.append({"skill": skill, "slug": meta["slug"], "language": meta.get("language", "ar"), "words": total, "not_in_second_extractor": n_unknown,
                        "rate": round(rate, 5), "second_extractor_only": missing,
                        "word_pairs": n_pairs, "pairs_not_in_second_extractor": bad_pairs,
                        "pair_rate": round(bad_pairs / n_pairs, 5) if n_pairs else 0.0,
                        "in_neither_extractor": sum(neither.values()),
                        "neither_examples": sorted(neither, key=neither.get, reverse=True)[:15],
                        "numbers": sum(my_nums.values()), "numbers_in_neither_extractor": sum(odd_nums.values()),
                        "number_examples": sorted(odd_nums)[:15],
                        "words_fewer_than_both_extractors": sum(dropped.values()),
                        "footnotes": meta.get("n_footnotes", 0), "footnotes_unplaced": meta.get("n_footnotes_unplaced", 0),
                        "footnote_numbers_missing": meta.get("footnote_numbers_missing", []),
                        "glyph_fixes": len(meta.get("glyph_fixes", [])),
                        "examples": sorted(unknown, key=unknown.get, reverse=True)[:15]})
        print(f"{skill}/{meta['slug']}: {total} words, {n_unknown} unmatched ({rate:.3%}); "
              f"word order: {bad_pairs}/{n_pairs} pairs differ ({(bad_pairs / n_pairs if n_pairs else 0):.3%})")
    out_name = "crosscheck-corpus.json" if only == {"maroc-corpus"} else "crosscheck.json"
    with open(os.path.join(REPO, "data", out_name), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    for lang in sorted({r["language"] for r in results}):
        rs = [r for r in results if r["language"] == lang]
        tot = sum(r["words"] for r in rs)
        bad = sum(r["not_in_second_extractor"] for r in rs)
        tp = sum(r["word_pairs"] for r in rs)
        bp = sum(r["pairs_not_in_second_extractor"] for r in rs)
        if tot and tp:
            print(f"      {lang}: words in neither other extractor {sum(r['in_neither_extractor'] for r in rs)}; "
                  f"numbers {sum(r['numbers'] for r in rs)}, in neither {sum(r['numbers_in_neither_extractor'] for r in rs)}; "
                  f"words fewer than both {sum(r['words_fewer_than_both_extractors'] for r in rs)}; "
                  f"footnotes {sum(r['footnotes'] for r in rs)}, unplaced {sum(r['footnotes_unplaced'] for r in rs)}, "
                  f"numbers skipped by the source or missed {sum(len(r['footnote_numbers_missing']) for r in rs)}")
            print(f"TOTAL {lang}: {len(rs)} texts, {tot} words, {bad} unmatched ({bad / tot:.3%}), "
                  f"worst text {max(r['rate'] for r in rs):.3%}; word-order pairs differing {bp}/{tp} ({bp / tp:.3%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
