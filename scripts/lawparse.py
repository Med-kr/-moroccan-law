#!/usr/bin/env python3
"""Turn extracted body lines of a Moroccan legal text into structured articles.

Input : body lines + footnotes from pdf_text.extract()
Output: dict with header info, parts (each a list of articles) and anomalies.

An article heading is a short standalone line such as
    المادة 43     الفصل 65-1     الفصل 85 مكرر     المادة الأولى
    الفصل السادس والثلاثون: الاختصاص
Which keyword (المادة / الفصل) marks articles is decided per document: the one
with more heading-like lines wins; the other one may be a chapter title.

Heading-like lines are then validated against the numbering sequence, so that a
wrapped cross-reference ("... المنصوص عليها في" / "المادة 30") is not mistaken
for the start of article 30.
"""
from __future__ import annotations

import re

NUM = r"\d+(?:\s?[-.–]\s?\d+)*"
SUFFIX = r"(?:\s*(?:مكرر(?:ة)?(?:\s*(?:مرتين|ثلاث مرات|أربع مرات|\d+))?|المكرر(?:ة)?))?"
_U = {"الأول": 1, "الأولى": 1, "الاول": 1, "الاولى": 1, "الحادي": 1, "الحادية": 1, "الواحد": 1, "الواحدة": 1, "الثاني": 2, "الثانية": 2,
      "الثالث": 3, "الثالثة": 3, "الرابع": 4, "الرابعة": 4, "الخامس": 5, "الخامسة": 5, "السادس": 6, "السادسة": 6,
      "السابع": 7, "السابعة": 7, "الثامن": 8, "الثامنة": 8, "التاسع": 9, "التاسعة": 9, "العاشر": 10, "العاشرة": 10}
_T = {"العشرون": 20, "العشرين": 20, "الثلاثون": 30, "الثلاثين": 30, "الأربعون": 40, "الأربعين": 40,
      "الخمسون": 50, "الخمسين": 50, "الستون": 60, "الستين": 60, "السبعون": 70, "السبعين": 70,
      "الثمانون": 80, "الثمانين": 80, "التسعون": 90, "التسعين": 90}
_SINGLE = {"الفريد": 1, "الفريدة": 1, "الوحيد": 1, "الوحيدة": 1}
_u = "|".join(sorted(_U, key=len, reverse=True))
_t = "|".join(_T)
ORD = rf"(?:(?:{_u})\s+عشرة?|(?:{_u})\s+و\s?(?:{_t})|(?:{_t})|(?:{_u})|{'|'.join(_SINGLE)})"
REF = r"((?:\s*\[\^\d+\])*)"
STRUCT_KW = ["الكتاب", "القسم", "الباب", "الجزء", "الفرع", "القسم الفرعي", "المبحث", "المطلب", "الفصل", "المادة"]
MONTHS = "يناير|فبراير|مارس|أبريل|ابريل|ماي|مايو|يونيو|يونيه|يوليو|يوليوز|غشت|أغسطس|شتنبر|سبتمبر|أكتوبر|اكتوبر|نونبر|نوفمبر|دجنبر|ديسمبر"
MAX_GAP = 12


def ordinal_value(s: str) -> int | None:
    w = s.split()
    if len(w) == 1:
        return _SINGLE.get(w[0]) or _T.get(w[0]) or (_U.get(w[0]) if w[0] not in ("الحادي", "الحادية", "الواحد", "الواحدة") else None)
    if len(w) == 2 and w[1] in ("عشر", "عشرة") and w[0] in _U:
        return 10 + _U[w[0]]
    joined = " ".join(w[1:]).replace("و ", "و")
    if w[0] in _U and joined.startswith("و") and joined[1:] in _T:
        return _T[joined[1:]] + _U[w[0]]
    return None


def heading_re(kw: str) -> re.Pattern:
    # groups: 1 refs-before, 2 number, 3 ordinal, 4 ordinal suffix, 5 refs-after, 6 title,
    #         7 text that follows the heading on the same line ("المادة الرابعة. - إذا نتج ...")
    return re.compile(rf"^{kw}{REF}\s*:?\s*(?:({NUM}{SUFFIX})|({ORD})({SUFFIX})){REF}\s*"
                      rf"(?::\s*(.{{0,90}})|\.\s*[-–]\s*(\S.*))?$")


FR_NUM = r"\d+(?:\s?[-.–]\s?\d+)*(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies))?"
FR_HEAD = re.compile(rf"^(?:Article|ARTICLE|Art\.){REF}\s*(?:({FR_NUM})|(premier|Premier|PREMIER|1er|unique|Unique|UNIQUE)){REF}\s*"
                     rf"(?::\s*(.{{0,90}})|\.?\s*[-–]\s*(\S.*))?$")
FR_STRUCT = ["Livre", "Partie", "Titre", "Chapitre", "Section", "Sous-section", "Paragraphe", "Article"]
FR_MONTHS = "janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre"


_QUAL = r"(?:ال)?(?:انتقالية|ختامية|عامة|مختلفة|زجرية|خاصة|متفرقة)"
UNNAMED_DIV = re.compile(rf"(?:ال)?(?:مقتضيات|أحكام|احكام)(?: \S+){{0,2}} {_QUAL}(?: و{_QUAL})?(?:\[\^\d+\])*|"
                         r"Dispositions (?:transitoires|finales|générales|diverses|pénales|communes)"
                         r"(?: et (?:transitoires|finales|diverses))?(?:\[\^\d+\])*")


def detect_lang(lines: list[dict]) -> str:
    """'fr' when the body is mostly written in Latin letters, else 'ar'."""
    sample = " ".join(l["t"] for l in lines[:4000])
    latin = len(re.findall(r"[A-Za-zÀ-ÿ]", sample))
    arabic = len(re.findall(r"[\u0621-\u064A]", sample))
    return "fr" if latin > arabic else "ar"


FR_HEAD_RUNON = re.compile(rf"^(?:Article|ARTICLE)\s+(?P<num>{FR_NUM})(?P<refs>(?:\[\^\d+\])+)\s+(?P<rest>[A-ZÀ-Ý«].*)$")


def match_heading_fr(t: str):
    # OCR-like slips in the PDFs: "Article 3l" (letter l / I for the digit 1)
    t = re.sub(r"^((?:Article|ARTICLE)\s+\d+)[lI](\d*)(?=[\s.:\-–\[]|$)", r"\g<1>1\g<2>", t)
    m = FR_HEAD.match(t)
    if not m:
        # "Article 353[^119] Lorsque ...": heading, footnote mark and text on one line, no separator
        r = FR_HEAD_RUNON.match(t)
        if r:
            return norm_num(r.group("num")), r.group("refs"), "", r.group("rest").strip()
    if not m:
        return None
    rest = (m.group(6) or "").strip()
    if len(t) - len(rest) > 130:
        return None
    num = norm_num(m.group(2)) if m.group(2) else "1"
    title = (m.group(5) or "").strip()
    if title.endswith((",", ";")):
        return None
    return num, (m.group(1) or "") + (m.group(4) or ""), re.sub(r"\[\^\d+\]", "", title).strip(), rest


def norm_num(raw: str) -> str:
    raw = re.sub(r"\s*([-.])\s*", r"\1", raw.strip().replace("–", "-"))
    return re.sub(r"\s+", " ", raw)


def first_int(num: str) -> int:
    m = re.match(r"\d+", num)
    return int(m.group()) if m else 0


def main_guess(num: str) -> int:
    """Main number of a heading that may still be written sub-first ("1-65")."""
    m = re.match(r"^(\d+)[-.](\d+)", num)
    return max(int(m.group(1)), int(m.group(2))) if m else first_int(num)


def match_heading(rx: re.Pattern, t: str):
    """Returns (num, refs, title, rest) or None. `rest` is article text that
    follows the heading on the same line."""
    m = rx.match(t)
    if not m:
        return None
    rest = (m.group(7) or "").strip()
    if len(t) - len(rest) > 130:
        return None
    if m.group(2):
        num = norm_num(m.group(2))
    else:
        v = ordinal_value(m.group(3))
        if v is None:
            return None
        num = (str(v) + " " + re.sub(r"^ال", "", (m.group(4) or "").strip()).replace("مكررة", "مكرر")).strip()
    title = (m.group(6) or "").strip()
    if title.endswith(("،", "؛")):
        return None
    return num, (m.group(1) or "") + (m.group(5) or ""), re.sub(r"\[\^\d+\]", "", title).strip(), rest


def pick_keyword(lines: list[dict]) -> str:
    """The word this text numbers its own articles with: the one whose headings form the longer
    valid sequence. (Counting every heading-like line is not enough: a law that amends a code
    quotes many "الفصل 404. - ..." of the code inside its own few "المادة".)"""
    best, best_n = "المادة", -1
    for kw in ("المادة", "الفصل"):
        rx = heading_re(kw)
        cands = []
        for idx, l in enumerate(lines):
            h = match_heading(rx, l["t"])
            if h:
                cands.append({"idx": idx, "num": h[0], "refs": h[1], "title": h[2], "rest": h[3],
                              "raw": l["t"], "page": l["p"], "inline": bool(h[3])})
        n = len(validate(cands)[0])
        if n > best_n:
            best, best_n = kw, n
    return best


def consolidation_date(lines: list[dict]) -> str | None:
    for l in lines[:60]:
        m = re.search(rf"[Vv]ersion\s+consolid[ée]e\s+(?:en\s+date\s+)?du\s+(.+?(?:{FR_MONTHS})\s+\d{{4}})", l["t"])
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
        m = re.search(rf"صيغة\s+محينة\s+بتاريخ\s+(.+?(?:{MONTHS})\s+\d{{4}})", l["t"])
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return None


def join_paragraphs(lines: list[str]) -> str:
    """Re-flow PDF lines into paragraphs."""
    paras: list[str] = []
    for t in lines:
        starts_item = bool(re.match(r"^(?:[-–•]|\d+\s*[-–.)]|[أ-ي]\s*[-–)])\s*", t))
        if paras and not starts_item and not re.search(r"[.؛;:!؟?]\s*(?:\[\^\d+\])*\s*$", paras[-1]):
            paras[-1] += " " + t
        else:
            paras.append(t)
    return "\n\n".join(paras)


def validate(cands: list[dict]) -> tuple[set[int], list[str]]:
    """Decide which heading-like lines really open an article.
    Returns (accepted line indexes, notes about rejected ones)."""
    accepted: set[int] = set()
    rejected: list[str] = []
    last = 0
    for i, c in enumerate(cands):
        num = c["num"]
        mm = re.match(r"^(\d+)([-.])(\d+)(.*)$", num)
        # right-to-left layout writes "65-1" as "1-65": put the main number first
        # (not "647-3" met after article 3: 647 is no sub-number, it is another law's article)
        if mm and int(mm.group(1)) <= last + MAX_GAP and (
                int(mm.group(1)) < last <= int(mm.group(3)) <= last + 3
                or (int(mm.group(3)) == last and int(mm.group(1)) != last)):
            num = c["num"] = f"{mm.group(3)}{mm.group(2)}{mm.group(1)}{mm.group(4)}"
        n = first_int(num)
        nxt = main_guess(cands[i + 1]["num"]) if i + 1 < len(cands) else None
        plain = re.fullmatch(r"\d+", num) is not None
        # "Article 50370": article 503 with footnote mark 70 printed at the same height
        want = str(last + 1)
        if (plain and last > 0 and n > last + MAX_GAP and num.startswith(want) and 1 <= len(num) - len(want) <= 3
                and not num[len(want):].startswith("0") and nxt is not None and last + 1 < nxt <= last + 4):
            c["refs"] += f"[^{num[len(want):]}]"
            num = c["num"] = want
            n = last + 1
        # "المادة 761-61": sub-article 61-1 (printed 1-61 right-to-left) with footnote mark 76 in front
        m2 = re.match(r"^(\d{2,5})-(\d+)$", num)
        if (m2 and int(m2.group(2)) == last and last > 0 and n > last + MAX_GAP
                and nxt is not None and last < nxt <= last + 3):
            head = m2.group(1)
            sub = head[-1]                       # the sub-number is one digit (61-1 ... 61-9)
            c["refs"] += f"[^{head[:-1]}]"
            num = c["num"] = f"{last}-{sub}"
            n = last
            plain = False
        # "المادة 231": article 31 with footnote mark 2 printed in front of the number (right-to-left)
        if (plain and last > 0 and n > last + MAX_GAP and num.endswith(want) and 1 <= len(num) - len(want) <= 3
                and nxt is not None and last + 1 < nxt <= last + 4):
            c["refs"] += f"[^{num[:len(num) - len(want)]}]"
            num = c["num"] = want
            n = last + 1
        ok = False
        # a later heading that would fill the hole means this one is a stray cross-reference
        fills = any(last < main_guess(x["num"]) < n for x in cands[i + 1:i + 9])
        twin = i + 1 < len(cands) and cands[i + 1]["num"] == num and not cands[i + 1].get("hanging")
        if c.get("hanging") and twin and not c["refs"]:
            ok = False      # "... المنصوص عليها في / الفصل الثاني عشر:" just before the real heading 12
        elif n > last + 1 and fills:
            ok = False
        elif n == last and not plain and last > 0:
            ok = True                                   # 65-1, 85 مكرر
        elif last < n <= last + MAX_GAP:
            ok = True
        elif n > last + MAX_GAP:
            # long repealed range: the next heading must follow on. Not for "647-1. - text" met
            # after article 3: that is an article of another law quoted by an amending law
            ok = nxt is not None and n <= nxt <= n + 3 and not c.get("inline")
        elif n < last and n == 1 and plain:
            ok = nxt is None or nxt in (1, 2)           # numbering restarts (promulgating dahir, annex)
            if ok:
                c["restart"] = True
        if ok:
            accepted.add(c["idx"])
            last = n
        else:
            rejected.append(f"heading-like line kept as text: '{c['raw'][:40]}' (page {c['page']})")
    return accepted, rejected


def parse(body: list[dict], notes: dict[str, str]) -> dict:
    lang = detect_lang(body)
    if lang == "fr":
        kw = "Article"
        heading = match_heading_fr
        struct_kws = [k for k in FR_STRUCT if k != kw]
        struct_rx = re.compile(rf"^({'|'.join(struct_kws)})\s+\S.{{0,140}}$", re.I)
        level: dict[str, int] = {}
        stops = (".", ";", ",")
        crossref = re.compile(r"\s(ci-dessus|ci-dessous|ci-après|du présent|de la présente|de la loi|du dahir|de l'article)", re.I)
    else:
        kw = pick_keyword(body)
        art_rx = heading_re(kw)
        heading = lambda t: match_heading(art_rx, t)
        struct_kws = sorted((k for k in STRUCT_KW if k != kw), key=len, reverse=True)   # "القسم الفرعي" before "القسم"
        struct_rx = re.compile(rf"^({'|'.join(struct_kws)})\s+\S.{{0,140}}$")
        level = {}
        stops = (".", "؛", "،")
        crossref = re.compile(r"\s(أعلاه|أدناه|من هذا|من القانون|من الظهير|من المادة|من الفصل)")

    # a title is centred; a line of body text starts at the margin. Used to tell the second line
    # of a two-line title from the first line of the text under a one-line title.
    xs0 = sorted(l["x0"] for l in body if "x0" in l)
    xs1 = sorted(l["x1"] for l in body if "x1" in l)
    left = xs0[len(xs0) // 20] if xs0 else 0
    right = xs1[-1 - len(xs1) // 20] if xs1 else 0

    def centred(l: dict) -> bool:
        if "x0" not in l or right <= left:
            return True
        w = right - left
        return l["x0"] - left > 0.06 * w and right - l["x1"] > 0.06 * w

    # Footnotes set in the body font are not caught by the extractor: "173 - تم إلغاء ..." printed
    # at the foot of the page. A line like that whose number is a mark used in the text and missing
    # from the notes is a note, not article text.
    marks = set(re.findall(r"\[\^(\d+)\]", " ".join(l["t"] for l in body)))
    words = r"(?:تم[ت]?\s|ألغي|نسخ|غير|انظر|راجع|Les dispositions|Abrog|Modifi|Voir|Cf\.)"
    note_rx = re.compile(rf"^(?:-?\s*(\d{{1,4}})\s*-|-(\d{{1,4}}))\s*({words}.*)$")
    kept = []
    last_note, note_page = None, None
    stray: set[str] = set()
    for l in body:
        m = note_rx.match(l["t"])
        num = m and (m.group(1) or m.group(2))
        if m and num in marks and (num not in notes or num in stray):
            last_note, note_page = num, l["p"]
            notes[num] = (notes[num] + " — " if num in stray else "") + m.group(3).strip()
            stray.add(num)
            continue
        # a note runs on only on its own page (the page after starts with body text)
        if (last_note and l["p"] == note_page and not re.search(r"[.؛;]\s*$", notes[last_note])
                and not heading(l["t"])):
            notes[last_note] += " " + l["t"]      # the note goes on on the next line
            continue
        last_note = None
        kept.append(l)
    body = kept

    # "المادة 231 يمنح ..." / "\"المادة 70 تطبق ...": an article heading run into its text with no
    # separator, sometimes in quotes (new wording) and sometimes with its footnote mark stuck in
    # front of the number. Accepted only under the strict conditions checked in validate().
    runon_rx = re.compile(rf"^([\"«]?)\s*{kw}\s+(\d{{1,6}}(?:-\d{{1,3}})?)(?:\s+(\S.*))?$") if lang == "ar" else None

    def runon(t: str):
        m = runon_rx.match(t) if runon_rx else None
        if not m or (m.group(3) is None and not m.group(1)) or crossref.match(" " + (m.group(3) or "")):
            return None
        num, rest = m.group(2), m.group(3) or ""
        for k in (1, 2, 3):                     # footnote mark + number, the note naming the article
            mark, real = num[:k], num[k:]
            if real and not real.startswith(("0", "-")) and mark in notes:
                flip = "-".join(reversed(real.split("-")))
                note = notes[mark]
                if re.search(rf"(?<![\d.\-]){re.escape(real)}(?![\d.\-])", note) or \
                        re.search(rf"(?<![\d.\-]){re.escape(flip)}(?![\d.\-])", note):
                    return flip if "-" in real and real != flip else real, f"[^{mark}]", "", rest, True
        return num, "", "", rest, False

    cands = []
    for idx, l in enumerate(body):
        h = heading(l["t"])
        if not h:
            r = runon(l["t"])
            if r:
                prev = body[idx - 1]["t"] if idx else ""
                cands.append({"idx": idx, "num": r[0], "refs": r[1], "title": "", "rest": r[3], "raw": l["t"],
                              "page": l["p"], "hanging": False, "inline": True,
                              "runon": "marked" if r[4] else "plain"})
            continue
        if h:
            prev = body[idx - 1]["t"] if idx else ""
            # the line before stops in mid-sentence: this may be the end of a wrapped cross-reference
            hanging = bool(prev) and not re.search(r"[.؛;:!؟?»\")]\s*(?:\[\^\d+\])*\s*$", prev) and not heading(prev)
            cands.append({"idx": idx, "num": h[0], "refs": h[1], "title": h[2], "rest": h[3], "raw": l["t"],
                          "page": l["p"], "hanging": hanging, "inline": bool(h[3])})
    # keep a run-on candidate only where it fills the numbering exactly: between the ordinary
    # headings around it, as the next article (or, with a mark naming it, as its sub-article)
    normal = [c for c in cands if not c.get("runon")]
    kept_cands = []
    for c in cands:
        if c.get("runon"):
            before = [x for x in normal if x["idx"] < c["idx"]]
            after = [x for x in normal if x["idx"] > c["idx"]]
            p_ = main_guess(before[-1]["num"]) if before else 0
            n_ = main_guess(after[0]["num"]) if after else None
            n = main_guess(c["num"])
            sub = "-" in c["num"]
            fits = (n == p_ + 1 and (n_ is None or n_ in (n + 1, n + 2))) or \
                   (sub and c["runon"] == "marked" and n == p_ and (n_ is None or n_ in (n + 1, n + 2)))
            if not fits:
                continue
        kept_cands.append(c)
    cands = kept_cands
    accepted, rejected = validate(cands)
    cand_by_idx = {c["idx"]: c for c in cands if c["idx"] in accepted}

    header_lines: list[str] = []
    parts: list[list[dict]] = []
    path: list[tuple[str, str]] = []
    cur: dict | None = None
    pending_struct = False
    pending_refs = ""          # footnote marks on structural titles: given to the next article
    used: set[str] = set()

    def close():
        nonlocal cur
        if cur:
            cur["text"] = join_paragraphs(cur.pop("lines"))
            refs: list[str] = []
            for r in re.findall(r"\[\^(\d+)\]", cur.pop("heading_refs") + cur["text"]):
                if r not in refs:
                    refs.append(r)
            cur["notes"] = {r: notes[r] for r in refs if r in notes and r not in used}
            used.update(cur["notes"])
            parts[-1].append(cur)
            cur = None

    for idx, l in enumerate(body):
        t = l["t"]
        c = cand_by_idx.get(idx)
        if c:
            close()
            pending_struct = False
            if not parts or c.get("restart"):
                parts.append([])
            heading = f"{kw} {c['num']}" + (f": {c['title']}" if c["title"] else "")
            cur = {"num": c["num"], "heading": heading, "heading_refs": pending_refs + c["refs"], "page": l["p"],
                   "path": [p[1] for p in path], "lines": [c["rest"]] if c["rest"] else []}
            pending_refs = ""
            continue
        # a division title with no keyword ("مقتضيات انتقالية وختامية", "Dispositions finales") right
        # before an article: it becomes the innermost level of the path, until the next titled division
        if not pending_struct and UNNAMED_DIV.fullmatch(t) and any(j in cand_by_idx for j in range(idx + 1, idx + 3)):
            close()
            while path and path[-1][0] == "_":
                path.pop()
            path.append(("_", t))
            pending_struct = False
            continue
        ms = struct_rx.match(t)
        # a structural title is short, does not end a sentence and is not a cross-reference
        if ms and not t.endswith(stops) and not crossref.search(t):
            close()
            k = ms.group(1).lower() if lang == "fr" else ms.group(1)
            # The nesting of divisions differs from one text to the next (الكتاب > القسم > الباب in
            # the code of obligations, الجزء > الباب > القسم in the customs code): a division's
            # rank is the order in which the text first uses it, outer divisions coming first.
            level.setdefault(k, len(level))
            while path and (path[-1][0] == "_" or level[path[-1][0]] >= level[k]):
                path.pop()
            path.append((k, re.sub(r"\[\^\d+\]", "", t).strip()))
            pending_refs += "".join(re.findall(r"\[\^\d+\]", t))
            pending_struct = True
            continue
        if cur is None:
            if pending_struct and path and len(t) < 90 and not t.endswith(stops + (":",)) and centred(l):
                k, title = path[-1]            # second line of a structural title
                path[-1] = (k, title + " " + re.sub(r"\[\^\d+\]", "", t).strip())
                pending_refs += "".join(re.findall(r"\[\^\d+\]", t))
                pending_struct = False
                continue
            pending_struct = False
            if not parts:
                header_lines.append(t)
                continue
            # text that sits between a structural title and the next article: keep it in place
            cur = {"num": "", "heading": "", "heading_refs": pending_refs, "page": l["p"],
                   "path": [p[1] for p in path], "lines": [t], "block": True}
            pending_refs = ""
            continue
        cur["lines"].append(t)
    close()

    header_notes = {}
    for r in re.findall(r"\[\^(\d+)\]", " ".join(header_lines)):
        if r in notes and r not in used:
            header_notes[r] = notes[r]
            used.add(r)
    # notes whose mark was not found anywhere (a mark on a title at the very end, or one the
    # extractor did not recognise as raised): they are printed at the end rather than lost
    orphan_notes = {k: v for k, v in notes.items() if k not in used}

    main_idx = max(range(len(parts)), key=lambda i: sum(1 for a in parts[i] if not a.get("block"))) if parts else 0
    anomalies: list[str] = list(rejected)
    if parts:
        prev = 0
        seen: dict[str, int] = {}
        for a in parts[main_idx]:
            if a.get("block"):
                continue
            n = first_int(a["num"])
            if a["num"] in seen:
                anomalies.append(f"duplicate article {a['num']} (pages {seen[a['num']]} and {a['page']})")
            seen[a["num"]] = a["page"]
            if n > prev + 1:
                anomalies.append(f"numbering gap: {prev} -> {a['num']} (page {a['page']}); usually a repealed range, check the footnote")
            prev = max(prev, n)
            if not a["text"].strip():
                anomalies.append(f"article {a['num']} has no text (page {a['page']}); usually repealed, check the footnote")

    return {
        "article_keyword": kw,
        "lang": lang,
        "consolidated_on": consolidation_date(body),
        "header": header_lines,
        "parts": parts,
        "main_part": main_idx,
        "n_articles": sum(1 for a in parts[main_idx] if not a.get("block")) if parts else 0,
        "anomalies": anomalies,
        "all_notes": notes,
        "header_notes": header_notes,
        "orphan_notes": orphan_notes,
    }
