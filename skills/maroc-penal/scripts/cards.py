#!/usr/bin/env python3
"""Article card: what a practitioner needs to know about one article before relying on it.

    cards.py <text> <article>            card of one article (text, as for law.py)
    cards.py <text> <article> --json     the same as JSON

The card is built from the official consolidated text itself, never from memory:
  status         in force as printed / amended / replaced / added / repealed, from the
                 footnotes of the source ("تم تغيير وتتميم", "تم نسخ وتعويض", "تمت إضافة",
                 "تم نسخ", "abrogé", "modifié et complété" ...);
  amendments     every amending text named in those footnotes (law, dahir or decree number,
                 article of the amending text) with its Bulletin officiel reference (issue,
                 date, page) found anywhere in the notes of the text: the first note that
                 cites an amending law gives the reference, later ones say "السالف الذكر";
  references     articles this one refers to (same text) and other laws it cites;
  version        consolidation date printed in the PDF, portal date, official link;
  warnings       documented source errors and divergences (article_notes, errata);
  counterpart    whether the other language version has this article, and its date.
Standard library only.
"""
from __future__ import annotations

import functools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import law  # noqa: E402

NOTE_LINE = re.compile(r"^\[\^(\d+)\]:\s*(.*(?:\n(?!\[\^|#|\n).*)*)", re.M)
LAW_NUM = re.compile(r"(?:(?:ال)?قانون(?:\s+(?:التنظيمي|المالية(?:\s+المعدل)?|(?:-\s*)?الإطار))?|(?:ال)?ظهير(?:\s+الشريف)?(?:\s+بمثابة\s+قانون)?|(?:ال)?مرسوم(?:\s+بقانون)?)"
                     r"\s+(?:رقم\s+)?(\d{1,3}(?:\.\d{1,4}){1,2})")
LAW_NUM_FR = re.compile(r"(?:loi(?:\s+organique)?|dahir(?:\s+portant\s+loi)?|décret(?:-loi)?)\s+n°\s*(\d{1,3}(?:[-.]\d{1,4}){1,2})", re.I)
BO = re.compile(r"الجريدة\s+الرسمية\s+عدد\s*(\d{3,5})(?:\s+\S+)?\s+بتاريخ\s+([^،,)]*?\((?:[^)]*)\)|[^،,]+?)\s*[،,]?\s*(?:ص\.?|الصفحة)\s*(\d+)")
BO_FR = re.compile(r"B\.?\s*O\.?\s*n°\s*(\d{3,5})\s+du\s+([^,;]+?)[,;]?\s*p\.?\s*(\d+)", re.I)
OF_ARTICLE = re.compile(r"(المادة|الفصل)\s+(الأولى|الأول|الفريدة|الثانية|الثاني|الثالثة|الثالث|الرابعة|الرابع|الخامسة|الخامس|\d+(?:-\d+)?)\s+من\s+(?:ال)?(?:قانون|ظهير|مرسوم)")
KINDS = [  # most specific first
    ("repealed", re.compile(r"تم\s+نسخ(?!\s+وتعويض)|نسخت|ألغي|ألغيت|تم\s+إلغاء|حذف|abrog|supprim", re.I)),
    ("replaced", re.compile(r"نسخ\s+وتعويض|نسخت\s+وعوضت|remplac", re.I)),
    ("added", re.compile(r"تمت?\s+إضافة|أضيفت|تم\s+تتميم\s+(?:ال)?(?:قانون|ظهير|مجموعة|مدونة|هذا\s+(?:القانون|الباب|الفرع))|"
                         r"تم\s+تتميم\s.{0,90}?\sب(?:ال)?(?:مادة|فصل|مواد|فصول|فرع|باب|قسم)|ajout|inséré|insérée", re.I)),
    ("amended", re.compile(r"تغيير|تتميم|غيرت|تممت|modifi|complét", re.I)),
]
INTERNAL_REF = re.compile(r"(?:المادة|المادتين|المواد|الفصل|الفصلين|الفصول|article|articles)\s+((?:\d+(?:-\d+)?(?:\s*(?:و|،|,|et|à|إلى)\s*)?)+)\s*(?:أعلاه|أدناه|بعده|قبله|من\s+هذا|ci-dessus|ci-dessous|du\s+présent)", re.I)


def text_notes(slug: str) -> dict[str, str]:
    with open(os.path.join(law.ROOT, slug, "text.md"), encoding="utf-8") as fh:
        return {n: " ".join(t.split()) for n, t in NOTE_LINE.findall(fh.read())}


def bo_index(notes: dict[str, str]) -> dict[str, dict]:
    """Amending-text number -> Bulletin officiel reference, from any note of the text."""
    out: dict[str, dict] = {}
    for t in notes.values():
        bos = [(m.start(), {"issue": m.group(1), "date": " ".join(m.group(2).split()), "page": m.group(3)})
               for m in list(BO.finditer(t)) + list(BO_FR.finditer(t))]
        if not bos:
            continue
        for m in list(LAW_NUM.finditer(t)) + list(LAW_NUM_FR.finditer(t)):
            num = m.group(1).replace("-", ".")
            after = [b for pos, b in bos if pos > m.start()]     # the reference that follows the law's name
            if after and num not in out:
                out[num] = after[0]
    return out


WHOLE_ADDED = re.compile(r"(?:تمت?\s+إضافة|أضيفت)\s*(?:أحكام\s+)?(?:ال)?(?:مادة|فصل|مواد|فصول|فرع|باب|قسم)|"
                         r"تم\s+تتميم\s.{0,90}?\sب(?:ال)?(?:مادة|فصل|مواد|فصول|فرع|باب|قسم)|"
                         r"(?:l[’']article|les\s+articles)\s+[\d\-– bistr]+\s+(?:a|ont)\s+été\s+(?:ajouté|inséré)", re.I)


def classify(note: str) -> str | None:
    for kind, rx in KINDS:
        if rx.search(note):
            # a paragraph or item added to an existing article is an amendment of that article
            if kind == "added" and not WHOLE_ADDED.search(note):
                return "amended"
            return kind
    return None


@functools.lru_cache(maxsize=8)
def _text(root: str, slug: str):
    """Articles, notes and Bulletin officiel index of a text, read once per text."""
    arts = law.load_articles(slug)
    by = {}
    for x in arts:
        by.setdefault(law.canon(x["num"]), x)
    notes_all = text_notes(slug)
    return by, notes_all, bo_index(notes_all)


def card(slug: str, num: str) -> dict:
    by, notes_all, bos = _text(law.ROOT, slug)
    a = by.get(law.canon(num))
    m = law.meta(slug)
    res: dict = {"text": slug, "law": m.get("title"), "law_fr": m.get("title_fr"), "article": num,
                 "language": m.get("language", "ar"),
                 "version": {"consolidated_on": m.get("consolidated_on"), "portal_updated": (m.get("source_updated_at") or "")[:10],
                             "source_url": m.get("source_url")},
                 "reviewed": "maroc-corpus" not in law.ROOT}
    if a is None:
        rep = law.repeal_notes(slug, num)
        res.update({"found": False, "status": "repealed" if rep else "not in this version",
                    "status_notes": rep, "amendments": [], "references": {}})
        return res
    res["article"] = a["num"]
    res["path"] = a["path"]
    own = dict(NOTE_LINE.findall(a["body"]))          # notes printed under the article
    marks = re.findall(r"\[\^(\d+)\]", a["body"])
    notes = {k: notes_all[k] for k in dict.fromkeys(marks) if k in notes_all}
    notes.update({k: " ".join(v.split()) for k, v in own.items()})
    amendments, kinds = [], []
    for k, t in notes.items():
        kind = classify(t)
        if not kind:
            continue
        kinds.append(kind)
        laws = [x.replace("-", ".") for x in LAW_NUM.findall(t) + LAW_NUM_FR.findall(t)]
        art_of = OF_ARTICLE.search(t)
        for n in dict.fromkeys(laws):
            amendments.append({"kind": kind, "by": n, "by_article": art_of.group(2) if art_of else None,
                               "bulletin_officiel": bos.get(n), "note": k})
        if not laws:
            amendments.append({"kind": kind, "by": None, "by_article": None, "bulletin_officiel": None, "note": k})
    body = NOTE_LINE.sub("", a["body"]).strip()
    if not body and "repealed" in kinds:
        status = "repealed"
    elif not body:
        status = "no text in this version"
    elif "added" in kinds:
        status = "added"
    elif "replaced" in kinds:
        status = "replaced"
    elif "amended" in kinds:
        status = "amended"
    else:
        status = "as printed (no amendment noted)"
    internal = sorted({x for g in INTERNAL_REF.findall(body) for x in re.findall(r"\d+(?:-\d+)?", g)},
                      key=lambda x: [int(p) for p in x.split("-")])
    external = sorted({x.replace("-", ".") for x in LAW_NUM.findall(body) + LAW_NUM_FR.findall(body)})
    warnings = []
    note = (m.get("article_notes") or {}).get(a["num"])
    if note:
        warnings.append(note)
    for c in m.get("source_corrections") or []:
        if re.search(rf"(?<![\d.]){re.escape(a['num'].split()[0])}(?![\d.])", c.get("replace", "")):
            warnings.append(f"erratum: {c['why']}")
    res.update({"found": True, "status": status, "amendments": amendments,
                "references": {"same_text": [x for x in internal if x != a["num"]], "other_texts": external},
                "warnings": warnings, "counterpart": counterpart(slug, a["num"])})
    return res


@functools.lru_cache(maxsize=16)
def _nums(root: str, slug: str) -> frozenset:
    return frozenset(law.canon(x["num"]) for x in law.load_articles(slug))


def counterpart(slug: str, num: str) -> dict | None:
    other = slug[:-3] if slug.endswith("-fr") else slug + "-fr"
    if other not in law.texts():
        return None
    nums = _nums(law.ROOT, other)
    om = law.meta(other)
    return {"text": other, "language": om.get("language", "ar"), "has_article": law.canon(num) in nums,
            "consolidated_on": om.get("consolidated_on")}


STATUS_AR = {"repealed": "منسوخة", "replaced": "منسوخة ومعوضة (صيغة جديدة)", "added": "مضافة بنص لاحق",
             "amended": "مغيرة أو متممة", "as printed (no amendment noted)": "كما صدرت (لا يشير النص إلى أي تعديل)",
             "no text in this version": "لا نص في هذه الصيغة", "not in this version": "غير موجودة في هذه الصيغة"}


def show(c: dict) -> None:
    v = c["version"]
    print(f"# بطاقة المادة / fiche — {c['law']} — {c['article']}")
    print(f"الحالة / statut: {STATUS_AR.get(c['status'], c['status'])} ({c['status']})")
    if not c.get("reviewed"):
        print("!! نص من المدونة الموسعة (استخراج آلي غير مراجع نصا نصا) / texte du corpus étendu, non relu")
    for s in c.get("status_notes") or []:
        print(f"  {s}")
    if c.get("amendments"):
        print("التعديلات / modifications:")
        for x in c["amendments"]:
            bo = x["bulletin_officiel"]
            ref = f" — الجريدة الرسمية عدد {bo['issue']} بتاريخ {bo['date']}، ص {bo['page']}" if bo else " — مرجع الجريدة الرسمية غير مذكور في الهوامش"
            by = f"{('المادة ' + x['by_article'] + ' من ') if x['by_article'] else ''}النص رقم {x['by']}" if x["by"] else "نص لم يحدد رقمه في الهامش"
            print(f"  - {x['kind']}: {by}{ref} [^{x['note']}]")
    refs = c.get("references") or {}
    if refs.get("same_text"):
        print(f"إحالات داخلية / renvois: {', '.join(refs['same_text'])}")
    if refs.get("other_texts"):
        print(f"نصوص أخرى مذكورة / autres textes cités: {', '.join(refs['other_texts'])}")
    for w in c.get("warnings") or []:
        print(f"!! {w}")
    cp = c.get("counterpart")
    if cp:
        print(f"النسخة الأخرى / autre version: {cp['text']} ({cp['language']}), "
              f"{'المادة موجودة' if cp['has_article'] else 'المادة غير موجودة'}, صيغة {cp['consolidated_on'] or 'غير مؤرخة'}")
    print(f"الصيغة / version: {v['consolidated_on'] or 'غير مذكورة في النص'} | Adala: {v['portal_updated']} | {v['source_url']}")


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    slug = law.resolve(argv[0])
    c = card(slug, argv[1])
    if "--json" in argv:
        print(json.dumps(c, ensure_ascii=False, indent=1))
    else:
        show(c)
    if not c["found"] and not c.get("status_notes"):
        sys.exit(3)


if __name__ == "__main__":
    main(sys.argv[1:])
