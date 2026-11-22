#!/usr/bin/env python3
"""Compare articles between two texts of this skill (for example a repealed law
and the law that replaced it). Standard library only.

    compare.py <text> <article> [--in <other text>] [--top N]
        the articles of the other text(s) whose wording is closest to this one
    compare.py table <text A> <text B> [--min 0.45]
        for every article of A, the closest article of B (tab-separated)

The link between two articles is a TEXTUAL SIMILARITY score computed by this
program (TF-IDF cosine on the Arabic words). It is a research aid, not an
official concordance table: always read both articles before concluding.
"""
from __future__ import annotations

import math
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import law  # noqa: E402

WORD = re.compile(r"[ء-ي]{2,}")
NOTE = re.compile(r"^\[\^\d+\]:.*$", re.M)
CAUTION = ("— تنبيه: الربط بين المواد أعلاه ناتج عن حساب آلي لتشابه الألفاظ، وليس جدول مقابلة رسميا. "
           "اقرأ النصين قبل أي استنتاج.\n— Attention : rapprochement calculé automatiquement (similarité "
           "textuelle), ce n'est pas une table de concordance officielle.")


def tokens(body: str) -> list[str]:
    body = re.sub(r"\[\^\d+\]", " ", NOTE.sub(" ", body))
    out = []
    for w in WORD.findall(law.norm(body)):
        if w.startswith("ال") and len(w) > 4:
            w = w[2:]
        out.append(w)
    return out


def vectors(arts: list[tuple[str, dict]]):
    """arts: [(slug, article)] -> list of normalised TF-IDF dicts."""
    tfs = [Counter(tokens(a["body"])) for _, a in arts]
    df = Counter()
    for tf in tfs:
        df.update(tf.keys())
    n = len(tfs)
    vecs = []
    for tf in tfs:
        v = {w: (1 + math.log(c)) * math.log(1 + n / df[w]) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs


def cos(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


def cmd_one(slug: str, num: str, others: list[str], top: int) -> None:
    src = law.load_articles(slug)
    hit = next((a for a in src if law.canon(a["num"]) == law.canon(num)), None)
    if hit is None:
        law.die(f"NOT FOUND in {slug}: {num}", 3)
    pool = [(o, a) for o in others for a in law.load_articles(o) if len(a["body"]) > 40]
    vecs = vectors([(slug, hit)] + pool)
    ranked = sorted(((cos(vecs[0], v), o, a) for v, (o, a) in zip(vecs[1:], pool)), key=lambda x: -x[0])[:top]
    print(f"# {law.meta(slug)['title']}")
    law.show(slug, hit)
    for score, o, a in ranked:
        if score < 0.12:
            break
        print(f"# تشابه {score:.2f} — {law.meta(o)['title']}")
        law.show(o, a)
    if not ranked or ranked[0][0] < 0.12:
        print("(لا توجد مادة ذات صياغة قريبة في النصوص المقارن بها)\n")
    print(CAUTION)


def cmd_table(a_slug: str, b_slug: str, floor: float) -> None:
    A = [(a_slug, a) for a in law.load_articles(a_slug) if len(a["body"]) > 40]
    B = [(b_slug, a) for a in law.load_articles(b_slug) if len(a["body"]) > 40]
    vecs = vectors(A + B)
    va, vb = vecs[:len(A)], vecs[len(A):]
    index: dict[str, list[int]] = {}
    for j, v in enumerate(vb):
        for w in v:
            index.setdefault(w, []).append(j)
    print(f"{a_slug}\t{b_slug}\tsimilarity")
    kept = 0
    for (_, a), v in zip(A, va):
        scores: dict[int, float] = {}
        for w, x in v.items():
            for j in index.get(w, ()):
                scores[j] = scores.get(j, 0.0) + x * vb[j][w]
        if not scores:
            continue
        j, s = max(scores.items(), key=lambda kv: kv[1])
        if s >= floor:
            kept += 1
            print(f"{a['num']}\t{B[j][1]['num']}\t{s:.2f}")
    print(f"# {kept} / {len(A)} articles of {a_slug} have a close article in {b_slug} (similarity >= {floor})")
    print(CAUTION)


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    opts = {"--in": None, "--top": "3", "--min": "0.45"}
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] in opts and i + 1 < len(argv):
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    if rest[0] == "table" and len(rest) == 3:
        cmd_table(law.resolve(rest[1]), law.resolve(rest[2]), float(opts["--min"]))
    elif len(rest) == 2:
        slug = law.resolve(rest[0])
        others = [law.resolve(opts["--in"])] if opts["--in"] else [t for t in law.texts() if t != slug]
        cmd_one(slug, rest[1], others, int(opts["--top"]))
    else:
        law.die(__doc__, 2)


if __name__ == "__main__":
    main(sys.argv[1:])
