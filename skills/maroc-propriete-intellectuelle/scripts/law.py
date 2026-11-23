#!/usr/bin/env python3
"""Look up Moroccan legal texts bundled with this skill. Standard library only.

    law.py list                          texts available in this skill
    law.py find <words>                  texts whose title contains the words
    law.py article <text> <n> [<n> ...]  exact text of one or more articles
                                         (ranges: 43..47 ; sub-articles: 65-1 ; "85 مكرر")
    law.py search <words> [--text T] [--max N] [--any]
                                         articles containing all the words (Arabic-insensitive
                                         to hamza/ta-marbuta/diacritics); --any = at least one
    law.py toc <text>                    table of contents with article ranges
    law.py card <text> <n> [--json]      status of an article: in force / amended / replaced / added /
                                         repealed, amending laws with their Bulletin officiel issue
    law.py both <text> <n> [<n> ...]     the Arabic article and its French version side by side
    law.py transitional <text>           transitional and final provisions (entry into force,
                                         repeals, pending cases): application in time
    law.py info <text>                   source, version date, extraction notes

<text> is the folder name under references/ (see `list`); a unique prefix works.
"""
from __future__ import annotations

import functools
import json
import math
import os
import re
import sys
import unicodedata

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references")
HEAD = re.compile(r"^## (المادة|الفصل|Article) (.+?)(?::\s*(.*))?$")   # number, then an optional title


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def texts() -> list[str]:
    if not os.path.isdir(ROOT):
        return []
    return sorted(d for d in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, d, "text.md")))


def resolve(name: str) -> str:
    all_ = texts()
    if name in all_:
        return name
    cands = [t for t in all_ if t.startswith(name)] or [t for t in all_ if name in t]
    if len(cands) > 1:       # "x" and "x-fr" (French version of the same text): prefer the Arabic one
        cands = [t for t in cands if not t.endswith("-fr")] or cands
    if len(cands) == 1:
        return cands[0]
    die(f"unknown or ambiguous text '{name}'. Available: {', '.join(all_)}")
    return ""


def meta(slug: str) -> dict:
    with open(os.path.join(ROOT, slug, "meta.json"), encoding="utf-8") as fh:
        return json.load(fh)


def load_articles(slug: str) -> list[dict]:
    """Parse text.md into [{num, heading, path, body}] (main body of the text only)."""
    arts: list[dict] = []
    cur = None
    path = ""
    with open(os.path.join(ROOT, slug, "text.md"), encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = HEAD.match(line)
            if m:
                title = (m.group(3) or "").strip()
                cur = {"num": m.group(2).strip(), "title": title, "path": path, "lines": [],
                       "heading": f"{m.group(1)} {m.group(2).strip()}" + (f": {title}" if title else "")}
                arts.append(cur)
                continue
            if line.startswith("# ") or line.startswith("## "):
                cur = None            # another section (preamble, annex) ends the article
                continue
            if line.startswith("> §"):
                path = line[3:].strip()
                continue
            if cur is not None:
                cur["lines"].append(line)
    for a in arts:
        a["body"] = "\n".join(a.pop("lines")).strip()
    return arts


def norm(s: str) -> str:
    s = re.sub(r"[ً-ٰٟـ]", "", s)
    s = re.sub(r"[أإآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")   # é -> e
    return s.lower()


def norm_num(s: str) -> str:
    s = s.strip().replace("–", "-")
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\bbis\b", "مكرر", s, flags=re.I)
    return re.sub(r"\s+", " ", s)


SUFFIXES = [  # longest first; Arabic and French names of the same suffix map to one key
    (r"مكرر(?:ة)? ثلاث مرات|quater", "quater"), (r"مكرر(?:ة)? مرتين|ter", "ter"),
    (r"(?:ال)?مكرر(?:ة)?|bis", "bis"),
]


def canon(num: str) -> str:
    """Comparison key for an article number: "353 bis", "353bis", "353 المكررة" and
    "353 مكرر" are the same article; so are 65-1, 65.1 and 65 - 1."""
    s = norm_num(num).lower()
    s = re.sub(r"\bqua\s+ter\b", "quater", s)          # "618-3 qua ter" (word split in the PDF)
    for rx, key in SUFFIXES:
        s = re.sub(rf"(?<![^\W\d_])\s*(?:{rx})\b", " " + key, s)   # whole word: "ter" is not the end of "quater"
    s = re.sub(r"^(?:1er|premier|unique|الأول|الأولى|الفريد|الفريدة|الوحيد|الوحيدة)$", "1", s)
    return re.sub(r"\s+", " ", s.replace(".", "-")).strip()


REPEAL = re.compile(r"ألغي|إلغاء|الغاء|نسخ|منسوخ|حذف|abrog|supprim", re.I)
RANGE = re.compile(r"(\d+)\s*(?:إلى|الى|حتى|à|au|-)\s*(?:المادة|الفصل|l[’']article)?\s*(\d+)", re.I)


def repeal_notes(slug: str, num: str) -> list[str]:
    """Footnotes of the text saying that this article (or a range containing it) was repealed."""
    m = re.match(r"\d+", num)
    if not m:
        return []
    n = int(m.group())
    out = []
    with open(os.path.join(ROOT, slug, "text.md"), encoding="utf-8") as fh:
        notes = re.findall(r"^\[\^\d+\]:.*(?:\n(?!\[\^|#|\n).*)*", fh.read(), re.M)
    for note in notes:
        if not REPEAL.search(note):
            continue
        flat = " ".join(note.split())
        nums = {int(x) for x in re.findall(r"(?<![\d.])(\d{1,4})(?![\d.])", flat)}
        in_range = any(int(a) <= n <= int(b) and int(b) - int(a) < 400 for a, b in RANGE.findall(flat))
        if (n in nums or in_range) and flat not in out:
            out.append(flat)
    return out[:3]


def footer(slug: str) -> str:
    m = meta(slug)
    if m.get("language") == "fr":
        ver = m.get("consolidated_on") or "non indiquée dans le texte"
        return (f"— {m['title_fr']} | version consolidée du : {ver} | {m.get('source_name') or 'source'} : {(m.get('source_updated_at') or '')[:10]} "
                f"| extraction : {m.get('extracted_at', '')[:10]}\n— Source officielle : {m['source_url']}\n"
                "— Version française : vérifier la date face à la version arabe, qui fait foi.")
    ver = m.get("consolidated_on") or "غير مذكور في النص"
    return (f"— {m['title']} | صيغة محينة بتاريخ: {ver} | {m.get('source_name') or 'source'}: {(m.get('source_updated_at') or '')[:10]} "
            f"| استخراج: {m.get('extracted_at', '')[:10]}\n— المصدر الرسمي: {m['source_url']}")


def show(slug: str, a: dict) -> None:
    print(f"## {a['heading']}")
    if a["path"]:
        print(f"({a['path']})")
    print()
    print(a["body"] if a["body"] else "(لا يوجد نص تحت هذا الرقم في الصيغة المحينة — راجع الهامش أو المصدر الرسمي)")
    print()
    note = (meta(slug).get("article_notes") or {}).get(a["num"])
    if note:
        print(f"!! {note}\n")


def cmd_list() -> None:
    for t in texts():
        m = meta(t)
        print(f"{t}\t{m['n_articles']} {m['article_keyword']}\t{m.get('consolidated_on') or '-'}\t{m['title']}")


def cmd_article(slug: str, nums: list[str]) -> None:
    arts = load_articles(slug)
    by = {}
    for a in arts:
        by.setdefault(canon(a["num"]), a)
    order = [a["num"] for a in arts]
    missing = []
    for raw in nums:
        m = re.fullmatch(r"(\d+)\.\.(\d+)", raw)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            hit = [a for a in arts if re.match(r"\d+", a["num"]) and lo <= int(re.match(r"\d+", a["num"]).group()) <= hi]
            if not hit:
                missing.append(raw)
            for a in hit:
                show(slug, a)
            continue
        hit = canon(raw)
        if hit in by:
            show(slug, by[hit])
        else:
            missing.append(raw)
    print(footer(slug))
    for x in missing:
        for note in repeal_notes(slug, x):
            print(f"\n{x} — هامش في النص يتعلق بالإلغاء أو النسخ / note de la source sur l'abrogation:\n{note}")
    if missing:
        near = [o for o in order if any(o.startswith(re.match(r"\d*", norm_num(x)).group() or "§") for x in missing)][:12]
        die(f"\nNOT FOUND in {slug}: {', '.join(missing)}" + (f"\nclosest numbers present: {', '.join(near)}" if near else ""), 3)


PREFIXES = ("وبال", "وال", "فال", "بال", "كال", "ولل", "فلل", "لل", "ال")
# Doctrinal or everyday words -> the wording the texts use (each pair checked in the text).
SYNONYMS = {
    "الشرط الجزائي": "التعويض المتفق عليه",          # DOC 264
    "الفترة التجريبية": "فترة الاختبار",               # labour code 13-14
    "فترة التجربة": "فترة الاختبار",
    "الطرد التعسفي": "الفصل التعسفي",                 # labour code 41
    "الطرد": "الفصل",
    "شيك بدون رصيد": "المؤونة الشيك",                 # commercial code 316
    "الشيك بدون رصيد": "المؤونة الشيك",
}


@functools.lru_cache(maxsize=None)
def stem(tok: str) -> str:
    """Search key of a word: diacritics, hamza seats, attached article and conjunction removed
    ("للأطر" and "الأطر", "بخطإه" and "بخطئه", "الآجال" and "آجال" give the same key)."""
    t = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", tok).replace("ى", "ي").replace("ة", "ه").lower()
    t = re.sub(r"^(?:l|d|qu|n|s)['’]", "", t)          # French elisions
    for p in PREFIXES:
        if t.startswith(p) and len(t) - len(p) >= 2:
            t = t[len(p):]
            break
    else:
        if t[:1] in ("و", "ف") and len(t) > 3:
            t = t[1:]
    # hamza seats before NFD, which would turn "إ" into "ا" and "ئ" into "ي"
    t = re.sub(r"^[أإآ]", "ا", t)
    t = t[:1] + re.sub(r"[ءأإآئؤ]", "", t[1:])
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


WORD = re.compile(r"[^\W_]+(?:[\u064B-\u065F\u0670\u0640]+[^\W_]*)*")


def keys(text: str) -> list[str]:
    return [stem(w) for w in WORD.findall(text) if not w.isdigit() or len(w) <= 4]


def expand(words: list[str]) -> list[list[list[str]]]:
    """Query -> groups; a group is satisfied by any of its alternatives (a sequence of keys)."""
    q = " ".join(words)
    groups = []
    for k, v in SYNONYMS.items():
        if k in q:
            groups.append([keys(k), keys(v)])
            q = q.replace(k, " ")
    groups += [[[x]] for x in keys(q)]
    return [g for g in groups if g and g[0]]


@functools.lru_cache(maxsize=None)
def light(k: str) -> str:
    """Light Arabic suffix folding, applied to text and query alike: attached pronouns after a
    ta marbuta ("استقالته" -> "استقاله"), plural endings ("مخالفات" -> "مخالفه", "معنيون" -> "معني").
    The bare final ه is never cut: after normalisation it is also the ta marbuta."""
    if not k or not ("\u0621" <= k[0] <= "\u064A"):
        return k
    for suf, rep, keep in (("تهما", "ه", 3), ("تهم", "ه", 3), ("تها", "ه", 3), ("ته", "ه", 3),
                           ("هما", "", 4), ("هم", "", 4), ("ها", "", 4), ("كم", "", 4), ("هن", "", 4),
                           ("ات", "ه", 3), ("ون", "", 3), ("ين", "", 4)):
        if k.endswith(suf) and len(k) - len(suf) >= keep:
            return k[: -len(suf)] + rep
    return k


@functools.lru_cache(maxsize=None)
def variants(k: str) -> frozenset[str]:
    """A word of the text also answers for itself without an attached preposition
    ("بتعليل" -> "تعليل"); only on the text side, so a query word is never cut."""
    out = {k, light(k)}
    if k[:1] in ("ب", "ل", "ك") and len(k) >= 4:
        out |= {k[1:], light(k[1:])}
    return frozenset(out)


def _has(seq: list[set[str]], alt: list[str]) -> bool:
    n = len(alt)
    return any(all(alt[j] in seq[i + j] for j in range(n)) for i in range(len(seq) - n + 1))


def cmd_search(words: list[str], only: str | None, limit: int, any_: bool) -> None:
    """Articles ranked by relevance. Default: every word (or a synonym) must be in the article
    or in its titles; with --any, or when nothing has them all, the best partial matches follow,
    marked as such."""
    groups = expand(words)
    if not groups:
        die("empty query", 2)
    slugs = [resolve(only)] if only else texts()
    docs = []
    for slug in slugs:
        for a in load_articles(slug):
            ks = keys(a["body"])
            seq = [variants(k) for k in ks]
            bag = set(ks).union(*(v for v in seq if len(v) > 1))
            title = set().union(*(variants(k) for k in keys(a["path"] + " " + a["heading"])))
            # the innermost section title and the article's own title: what the article is about
            own = a["path"].split(" › ")[-1] + " " + a.get("title", "")
            section = set().union(*(variants(k) for k in keys(own))) if own.strip() else set()
            docs.append((slug, a, seq, bag, title, section))
    n = len(docs) or 1
    groups = [[[light(x) for x in alt] for alt in g] for g in groups]     # query folded like the text
    df = {}
    for g in groups:
        for alt in g:
            for x in alt:
                if x not in df:
                    df[x] = sum(1 for d in docs if x in d[3])
    idf = lambda x: math.log(1 + n / (1 + df.get(x, 0)))
    weight = [max(sum(idf(x) for x in alt) for alt in g) for g in groups]
    full, partial = [], []
    for slug, a, seq, bag, title, section in docs:
        score, hit = 0.0, 0
        for g, w in zip(groups, weight):
            if any((alt[0] in bag if len(alt) == 1 else _has(seq, alt)) for alt in g):
                tf = max(sum(1 for v in seq if alt[0] in v) for alt in g) if len(groups) > 1 else 1
                score += w * (1 + 0.5 * math.log(max(tf, 1)))
                hit += 1
            elif any(all(x in title for x in alt) for alt in g):
                score += 0.6 * w
                hit += 1
        if not hit:
            continue
        in_section = sum(1 for g in groups if any(all(x in section for x in alt) for alt in g))
        if in_section:
            score *= 1 + 0.15 * in_section / len(groups)  # the section is about the question's subject
        joined = [x for g in groups for x in g[0]]
        if len(groups) > 1 and _has(seq, joined):
            score *= 2.0                                    # the words appear together, in order
        head = seq[:30]
        if sum(1 for g in groups if any(all(any(x in v for v in head) for x in alt) for alt in g)) == len(groups):
            score *= 1.3                                    # the article opens on the subject (a definition, the rule)
        score /= 1 + 0.15 * math.log(1 + len(seq) / 120)    # long articles mention everything
        (full if hit == len(groups) else partial).append((score, hit, slug, a))
    full.sort(key=lambda r: -r[0])
    partial.sort(key=lambda r: (-r[1], -r[0]))
    rows = [(r, "") for r in full[:limit]]
    if any_ or len(rows) < limit:
        need = limit - len(rows)
        rows += [(r, f" (جزئي {r[1]}/{len(groups)})") for r in partial[:need] if r[1] * 2 >= len(groups)]
    if not rows:
        die("no article matches. Try fewer or different words (--any), or another skill/text.", 3)
    by_slug: dict[str, list] = {}
    for (score, hit, slug, a), tag in rows:
        by_slug.setdefault(slug, []).append((a, tag))
    qk = [x for g in groups for x in g[0]]
    for slug, items in by_slug.items():
        print(f"# {slug} — {len(items)} نتيجة (مرتبة حسب الصلة / par pertinence)")
        for a, tag in items:
            flat = a["body"].replace("\n", " ")
            words_ = WORD.findall(flat)
            pos = next((i for i, w in enumerate(words_) if variants(stem(w)) & set(qk)), 0)
            i = flat.find(words_[pos]) if words_ else 0
            print(f"- {a['heading']}{tag}: …{flat[max(0, i - 90): i + 210]}…")
    extra = len(full) - min(len(full), limit)
    if extra > 0:
        print(f"  (+{extra} أخرى — استعمل --max)")


TRANSITION_TITLE = re.compile(r"انتقالي|ختامي|transitoire|finale", re.I)
TRANSITION_BODY = re.compile(r"حيز التنفيذ|يعمل بهذا|يعمل بأحكام|يدخل هذا|تنسخ|تلغى|تظل .{0,40}سارية|الجارية|الرائجة|"
                             r"القضايا المعروضة|entre(?:nt)? en vigueur|sont abrogé|demeurent applicables|en cours", re.I)


def cmd_transitional(slug: str) -> None:
    """Transitional and final provisions: entry into force, repeals, pending cases."""
    arts = load_articles(slug)
    hits = [a for a in arts if TRANSITION_TITLE.search(a["path"].split(" › ")[-1] if a["path"] else "")
            or TRANSITION_TITLE.search(a["heading"])]
    tail = arts[-15:]
    hits += [a for a in tail if a not in hits and TRANSITION_BODY.search(a["body"])]
    if not hits:
        print("(لا توجد أحكام انتقالية أو ختامية معنونة في هذا النص — ابحث عن 'حيز التنفيذ' بالأداة search)")
    for a in hits:
        show(slug, a)
    print(footer(slug))
    print("— Application dans le temps : lire ces articles avant de répondre pour des faits, actes ou procédures "
          "antérieurs à la réforme. / تطبيق القانون من حيث الزمان: اقرأ هذه المواد قبل الجواب عن وقائع أو "
          "مساطر سابقة على النص.")


def cmd_both(slug: str, nums: list[str]) -> None:
    """The same articles in the Arabic text and its French version, with both version dates:
    the Arabic text prevails, and the French one is often older."""
    ar = slug[:-3] if slug.endswith("-fr") else slug
    fr = ar + "-fr"
    if fr not in texts():
        die(f"no French version of {ar} in this skill", 3)
    for s_ in (ar, fr):
        m = meta(s_)
        print(f"=== {'AR' if s_ == ar else 'FR'} — {m['title']} — version: {m.get('consolidated_on') or '—'}")
        by = {canon(a["num"]): a for a in load_articles(s_)}
        for n in nums:
            a = by.get(canon(n))
            if a:
                show(s_, a)
            else:
                print(f"## {n}: NOT FOUND in this version\n")
    print("— النص العربي هو المعتمد. La version arabe fait foi ; vérifier les dates des deux versions.")


def cmd_find(words: list[str], limit: int = 15) -> None:
    """Texts of this skill whose title contains the words (Arabic-insensitive): the way into a
    skill that holds hundreds of texts."""
    joined = " ".join(words)
    numbers = [n.replace("-", ".") for n in re.findall(r"\d+[.\-]\d+(?:[.\-]\d+)?", joined)]
    q = keys(re.sub(r"\d+[.\-]\d+(?:[.\-]\d+)?", " ", joined))
    rows = []
    for t in texts():
        m = meta(t)
        title = f"{m.get('title', '')} {m.get('source_title', '')}"
        if numbers:
            flat = title.replace("-", ".")
            if not all(re.search(rf"(?<![\d.]){re.escape(n)}(?![\d.])", flat) for n in numbers):
                continue
            if not q:
                rows.append((1, -len(title), t, m))
                continue
        tk = set().union(*(variants(k) for k in keys(title))) if title.strip() else set()
        hit = sum(1 for x in q if x in tk)
        if hit:
            rows.append((hit, -len(title), t, m))
    rows.sort(key=lambda r: (-r[0], r[1]))
    if not rows:
        die("no text title matches; try other words, or the catalog (maroc-droit).", 3)
    for hit, _, t, m in rows[:limit]:
        print(f"{t}\t{m['n_articles']} {m['article_keyword']}\t{m.get('consolidated_on') or '-'}\t{m['title']}")


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    if cmd == "list":
        cmd_list()
    elif cmd == "article" and len(rest) >= 2:
        cmd_article(resolve(rest[0]), rest[1:])
    elif cmd == "search" and rest:
        only, limit, any_, words = None, 15, False, []
        i = 0
        while i < len(rest):
            if rest[i] == "--text" and i + 1 < len(rest):
                only = rest[i + 1]; i += 2
            elif rest[i] == "--max" and i + 1 < len(rest):
                limit = int(rest[i + 1]); i += 2
            elif rest[i] == "--any":
                any_ = True; i += 1
            else:
                words.extend(rest[i].split()); i += 1    # a quoted phrase is several words
        cmd_search(words, only, limit, any_)
    elif cmd == "toc" and rest:
        with open(os.path.join(ROOT, resolve(rest[0]), "toc.md"), encoding="utf-8") as fh:
            print(fh.read())
    elif cmd == "card" and len(rest) >= 2:
        import cards                                    # same folder
        c = cards.card(resolve(rest[0]), rest[1])
        if "--json" in rest:
            print(json.dumps(c, ensure_ascii=False, indent=1))
        else:
            cards.show(c)
        if not c["found"] and not c.get("status_notes"):
            sys.exit(3)
    elif cmd == "both" and len(rest) >= 2:
        cmd_both(resolve(rest[0]), rest[1:])
    elif cmd == "find" and rest:
        cmd_find(rest)
    elif cmd == "transitional" and rest:
        cmd_transitional(resolve(rest[0]))
    elif cmd == "info" and rest:
        print(json.dumps(meta(resolve(rest[0])), ensure_ascii=False, indent=1))
    else:
        die(__doc__, 2)


if __name__ == "__main__":
    main(sys.argv[1:])
