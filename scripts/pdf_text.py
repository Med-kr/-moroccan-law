#!/usr/bin/env python3
"""Extract clean, logical-order text from the legal PDFs published on Adala.

Pipeline
--------
1. Repair the fonts' ToUnicode CMaps. The PDFs map each lam-alef ligature glyph
   to a *pair* of code points; text extractors mirror that pair inside
   right-to-left runs, so "خلال" comes out as "خالل". We store every
   multi-code-point Arabic target reversed so it comes out right.
2. Run pdf.js (scripts/extract.mjs) on the repaired file to get positioned
   lines, with words rebuilt from glyph geometry and raised digits turned into
   footnote references ([^12]).
3. Split each page into body lines and footnote lines (smaller font at the
   bottom of the page) and drop page-number lines.

Requires: pymupdf, node >= 18 with pdfjs-dist installed (npm install).

    uv run --with pymupdf python scripts/pdf_text.py in.pdf out.txt
"""
from __future__ import annotations

import collections
import json
import os
import re
import subprocess
import sys
import tempfile

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
HEX = r"[0-9A-Fa-f]"
ARABIC_UNIT = re.compile(r"^(06..|FB[5-9A-F].|FE[7-9A-F].)$", re.I)
BIDI_CTRL = dict.fromkeys(map(ord, "‎‏‪‫‬‭‮⁦⁧⁨⁩﻿​"))
# symbol-font bullets and look-alike letters found in the source PDFs
GLYPH_FIX = {0x00A0: " ", 0xF02D: "-", 0xF0B7: "•", 0xF0A7: "•", 0xF049: None, 0x06CC: "ي", 0x06A9: "ك", 0x0640: None}
# Symbol-font private-use code points are ASCII + 0xF000 (U+F025 is "%")
for _c in range(0xF020, 0xF07F):
    GLYPH_FIX.setdefault(_c, chr(_c - 0xF000))
PAGE_NO = re.compile(r"^\s*-{0,2}\s*\d{1,4}\s*-{0,2}\s*$")   # "- 4 -", and "4 --" as right-to-left lines give it


# --------------------------------------------------------------------------
# 1. ToUnicode repair
# --------------------------------------------------------------------------
def _units(h: str) -> list[str]:
    return [h[i:i + 4] for i in range(0, len(h), 4)]


def _is_multi_arabic(h: str) -> bool:
    u = _units(h)
    return len(h) % 4 == 0 and 2 <= len(u) <= 4 and all(ARABIC_UNIT.match(x) for x in u)


def _rev(h: str) -> str:
    return "".join(reversed(_units(h)))


def _fix_bfchar(block: str) -> tuple[str, int]:
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        src, dst = m.group(1), m.group(2)
        # glyph 3 is the space of the TrueType fonts these files embed; a few files map it to
        # the letter heh, which glues every pair of words with a stray "ه"
        if src.upper() == "0003" and dst.upper() == "0647":
            n += 1
            return f"<{src}> <0020>"
        if _is_multi_arabic(dst):
            n += 1
            dst = _rev(dst)
        return f"<{src}> <{dst}>"

    return re.sub(rf"<({HEX}+)>\s*<({HEX}+)>", sub, block), n


def _fix_bfrange(block: str) -> tuple[str, int]:
    n = 0
    out = []
    pos = 0
    entry = re.compile(rf"<({HEX}+)>\s*<({HEX}+)>\s*(\[[^\]]*\]|<{HEX}+>)")
    for m in entry.finditer(block):
        out.append(block[pos:m.start()])
        pos = m.end()
        lo, hi, dst = m.group(1), m.group(2), m.group(3)
        if dst.startswith("["):
            items = re.findall(rf"<({HEX}+)>", dst)
            # some files map the isolated lam-alef glyph to a lone lam although its
            # neighbours in the same glyph run are lam-alef pairs: restore the alef
            lam_alef = {"06440627", "06440623", "06440625", "06440622"}
            for i, it in enumerate(items):
                near = items[max(0, i - 1):i] + items[i + 1:i + 2]
                if it.upper() == "0644" and any(x.upper() in lam_alef for x in near):
                    items[i] = "06440627"
            new = []
            for it in items:
                if _is_multi_arabic(it):
                    n += 1
                    it = _rev(it)
                new.append(f"<{it}>")
            out.append(f"<{lo}> <{hi}> [{' '.join(new)}]")
        else:
            base = dst[1:-1]
            if _is_multi_arabic(base):
                # a range increments the LAST code point; expand before reversing
                units = _units(base)
                count = int(hi, 16) - int(lo, 16) + 1
                arr = []
                for i in range(count):
                    last = f"{int(units[-1], 16) + i:04X}"
                    arr.append("<" + _rev("".join(units[:-1] + [last])) + ">")
                    n += 1
                out.append(f"<{lo}> <{hi}> [{' '.join(arr)}]")
            else:
                out.append(m.group(0))
    out.append(block[pos:])
    return "".join(out), n


def parse_cmap(txt: str) -> dict[int, str]:
    """ToUnicode CMap -> {glyph code: target code points as upper-case hex}."""
    out: dict[int, str] = {}
    for blk in re.findall(r"beginbfchar(.*?)endbfchar", txt, re.S):
        for a, b in re.findall(rf"<({HEX}+)>\s*<({HEX}+)>", blk):
            out[int(a, 16)] = b.upper()
    for blk in re.findall(r"beginbfrange(.*?)endbfrange", txt, re.S):
        for lo, hi, dst in re.findall(rf"<({HEX}+)>\s*<({HEX}+)>\s*(\[[^\]]*\]|<{HEX}+>)", blk):
            a, b = int(lo, 16), int(hi, 16)
            if dst.startswith("["):
                for i, it in enumerate(re.findall(rf"<({HEX}+)>", dst)):
                    out[a + i] = it.upper()
            else:
                base = dst[1:-1]
                for i in range(b - a + 1):
                    out[a + i] = (base[:-4] + f"{int(base[-4:], 16) + i:04X}").upper()
    return out


def _write_cmap(mapping: dict[int, str]) -> bytes:
    items = sorted(mapping.items())
    parts = ["/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
             "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
             "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
             "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"]
    for i in range(0, len(items), 100):
        chunk = items[i:i + 100]
        parts.append(f"{len(chunk)} beginbfchar\n")
        parts.extend(f"<{g:04X}> <{u}>\n" for g, u in chunk)
        parts.append("endbfchar\n")
    parts.append("endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n")
    return "".join(parts).encode("latin-1")


def type0_fonts(doc: pymupdf.Document) -> list[tuple[str, int]]:
    """(base font name without subset prefix, xref of its ToUnicode stream) of every composite font."""
    out = []
    for xref in range(1, doc.xref_length()):
        try:
            obj = doc.xref_object(xref, compressed=True)
        except Exception:
            continue
        if "/Type0" not in obj or "/ToUnicode" not in obj or "Identity-H" not in obj:
            continue
        tu = re.search(r"/ToUnicode\s+(\d+)\s+0\s+R", obj)
        bf = re.search(r"/BaseFont\s*/([^\s/<>\[\]]+)", obj)
        if not tu or not bf:
            continue
        name = re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), bf.group(1)).split("+")[-1]
        out.append((name, int(tu.group(1))))
    return out


def _chars(u: str) -> str:
    return "".join(chr(int(x, 16)) for x in _units(u))


def _has_arabic(u: str) -> bool:
    return any("\u0600" <= c <= "\u06FF" for c in _chars(u))


GLYPH_TABLE_PATH = os.path.join(os.path.dirname(HERE), "data", "glyph-table.json")
_GLYPH_TABLE: dict | None = None


def glyph_table() -> dict[str, dict[int, str]]:
    """Reference glyph -> text table per font, voted over every source PDF (scripts/glyph_table.py)."""
    global _GLYPH_TABLE
    if _GLYPH_TABLE is None:
        try:
            with open(GLYPH_TABLE_PATH, encoding="utf-8") as fh:
                raw = json.load(fh)["fonts"]
            _GLYPH_TABLE = {name: {int(g, 16): u for g, u in tab.items()} for name, tab in raw.items()}
        except (OSError, ValueError, KeyError):
            _GLYPH_TABLE = {}
    return _GLYPH_TABLE


def _apply_glyph_table(doc: pymupdf.Document) -> list[dict]:
    """Correct single wrong entries of a font's ToUnicode map from the reference table.

    Word writes these maps while laying text out, and now and then records the wrong letter
    for a glyph (a kashida read as dal, the "alef with madda" read as a bare alef, a letter
    read as a space). The same font embedded in the other laws has the right entry, so the
    glyph is looked up there. Only done when the font demonstrably is the same one (its other
    Arabic entries agree with the table), and only towards Arabic text: Latin punctuation is
    mirrored differently in right-to-left and left-to-right files and is left alone."""
    table = glyph_table()
    fixes: list[dict] = []
    done: set[int] = set()
    for name, xref in type0_fonts(doc):
        ref = table.get(name)
        if not ref or xref in done:
            continue
        done.add(xref)
        mapping = parse_cmap(doc.xref_stream(xref).decode("latin-1"))
        shared = [g for g in mapping if g in ref and _has_arabic(ref[g])]
        agree = sum(1 for g in shared if sorted(_chars(mapping[g])) == sorted(_chars(ref[g])))
        if len(shared) < 20 or agree / len(shared) < 0.9:
            continue
        changed = False
        for g in shared:
            cur, want = mapping[g], ref[g]
            if sorted(_chars(cur)) == sorted(_chars(want)):
                continue
            if not (_has_arabic(cur) or not _chars(cur).strip()):
                continue
            fixes.append({"font": name, "glyph": f"{g:04X}", "was": _chars(cur), "now": _chars(want)})
            mapping[g] = want
            changed = True
        if changed:
            doc.update_stream(xref, _write_cmap(mapping))
    return fixes


def patch_cmaps(doc: pymupdf.Document, use_table: bool = True, fixes: list | None = None) -> int:
    """Repair every ToUnicode CMap: multi-code-point Arabic targets are stored reversed, and
    (use_table) single wrong entries are corrected from the reference glyph table.
    Returns the number of mappings rewritten; the table corrections are appended to `fixes`."""
    total = 0
    for xref in range(1, doc.xref_length()):
        try:
            if not doc.xref_is_stream(xref):
                continue
            raw = doc.xref_stream(xref)
        except Exception:
            continue
        if not raw or (b"beginbfchar" not in raw and b"beginbfrange" not in raw):
            continue
        txt = raw.decode("latin-1")
        n_here = 0

        def do_char(m: re.Match) -> str:
            nonlocal n_here
            body, k = _fix_bfchar(m.group(2))
            n_here += k
            return m.group(1) + body + m.group(3)

        def do_range(m: re.Match) -> str:
            nonlocal n_here
            body, k = _fix_bfrange(m.group(2))
            n_here += k
            return m.group(1) + body + m.group(3)

        txt = re.sub(r"(beginbfchar)(.*?)(endbfchar)", do_char, txt, flags=re.S)
        txt = re.sub(r"(beginbfrange)(.*?)(endbfrange)", do_range, txt, flags=re.S)
        if n_here:
            doc.update_stream(xref, txt.encode("latin-1"))
            total += n_here
    if use_table:
        got = _apply_glyph_table(doc)
        total += len(got)
        if fixes is not None:
            fixes.extend(got)
    return total


# --------------------------------------------------------------------------
# 2-3. pdf.js lines -> body / footnotes
# --------------------------------------------------------------------------
def _clean_line(s: str) -> str:
    s = s.translate(BIDI_CTRL).translate(GLYPH_FIX)
    s = re.sub(r"\s+([،؛.:,;!?»)\]])", r"\1", s)      # no space before closing punctuation
    s = re.sub(r"([(\[«])\s+", r"\1", s)               # no space after opening punctuation
    s = re.sub(r"([،؛])(?=[^\s\d)\]»\"'])", r"\1 ", s)  # space after Arabic comma/semicolon
    s = re.sub(r"((?:الفصل|المادة|الفصول|المواد|الفصلين|المادتين|و|أو|إلى)\s)-\s?(\d{1,2})\s(\d{1,4})(?!\d)", r"\1\3-\2", s)
    s = re.sub(r"((?:الفصل|المادة)\s\d{1,4})\s-(\d{1,2})(?!\d)", r"\1-\2", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def read_pages(pdf_path: str) -> tuple[list[dict], dict]:
    doc = pymupdf.open(pdf_path)
    n_pages = doc.page_count
    glyph_fixes: list[dict] = []
    patched = patch_cmaps(doc, fixes=glyph_fixes)
    with tempfile.TemporaryDirectory() as tmp:
        fixed = os.path.join(tmp, "fixed.pdf")
        doc.save(fixed)
        doc.close()
        res = subprocess.run(["node", os.path.join(HERE, "extract.mjs"), fixed],
                             capture_output=True, check=True)
        try:
            second = subprocess.run(["pdftotext", "-enc", "UTF-8", fixed, "-"], capture_output=True, check=True)
            vocab = set(AR_WORD.findall(second.stdout.decode("utf-8", "replace").translate(BIDI_CTRL).translate(GLYPH_FIX)))
        except (OSError, subprocess.CalledProcessError):
            vocab = set()
    pages = [json.loads(l) for l in res.stdout.decode("utf-8").splitlines() if l.strip()]
    merged = 0
    if vocab:
        for pg in pages:
            for l in pg["lines"]:
                l["t"], k = rejoin_split_words(l["t"].translate(BIDI_CTRL).translate(GLYPH_FIX), vocab)
                merged += k
    return pages, {"pages": n_pages, "cmap_fixes": patched, "glyph_fixes": glyph_fixes, "split_words_rejoined": merged}


AR_WORD = re.compile(r"[\u0621-\u064A]+")
_PAIR = re.compile(r"(?<![\u0621-\u064A])([\u0621-\u064A]+) ([\u0621-\u064A]+)(?![\u0621-\u064A])")


def rejoin_split_words(line: str, vocab: set[str]) -> tuple[str, int]:
    """pdf.js sometimes sees a space inside a word (wide gap after a non-joining
    letter). When a second extractor (poppler) knows the joined word but not
    both halves, join them."""
    n = 0
    for _ in range(4):
        changed = False

        def sub(m: re.Match) -> str:
            nonlocal n, changed
            a, b = m.group(1), m.group(2)
            if (a not in vocab or b not in vocab) and (a + b) in vocab:
                n += 1
                changed = True
                return a + b
            return m.group(0)

        line = _PAIR.sub(sub, line)
        if not changed:
            break
    return line, n


_NOTE_A = re.compile(r"^-?\s*(\d{1,4})\s*-\s*(.*)$")
_NOTE_B = re.compile(r"^-\s*(\d{1,4})\s+(.*)$")


_NOTE_C = re.compile(r"^(\d{1,4})\s+(\S.*)$")
_SENTENCE_END = (".", ")", "»", '"', "”", "؛", ";", ":")


def _follows(n: int, last: int, nxt: int | None) -> bool:
    """Is n the next footnote number after `last`? Normally last+1; the files skip a number now
    and then, so a jump is accepted when small, or when the following note continues from n
    (242, 245, 246 ...). A stray "- 24 ساعة" inside note 19 is followed by note 20: refused."""
    if not last < n:
        return False
    return n <= last + 2 or (n <= last + 12 and nxt is not None and n < nxt <= n + 2)


def note_start(l: dict, t: str, last: int | None = None, after_stop: bool = True,
               nxt: int | None = None) -> tuple[list[str], str] | None:
    """(["12"], "text") when the line opens footnote 12, else None. Several numbers when one
    note serves several marks ("13-14 ...").

    Footnotes are numbered in one rising sequence through the whole document; `last` is the
    number of the previous note. Recognised, in order of reliability:
    - a line that opens with small raised numbers (`mark`, set by extract.mjs);
    - "12 - text" and "-12 text", when 12 comes shortly after `last`;
    - a bare "12 text", only when 12 is exactly the next number and the line before ended a
      sentence (a wrapped date such as "22 من ربيع الأول" must not open note 22).
    With last=None the sequence is not checked (used to find the footnote font)."""
    if PAGE_NO.match(t):
        return None
    if l.get("mark"):
        nums = [n for n in l["mark"] if last is None or n > last]
        if nums and (last is None or _follows(nums[0], last, nxt) or nums[0] <= last + 8):
            return [str(n) for n in nums], t
        return None
    m = _NOTE_A.match(t) or _NOTE_B.match(t)
    if m:
        n = int(m.group(1))
        if last is None or _follows(n, last, nxt):
            return [m.group(1)], m.group(2).strip()
        return None
    m = _NOTE_C.match(t)
    if m and (last is None or (int(m.group(1)) == last + 1 and after_stop)):
        return [m.group(1)], m.group(2).strip()
    return None


def split_body_footnotes(pages: list[dict]) -> tuple[list[dict], dict[str, str], dict]:
    """Returns (body_lines, footnotes, stats).
    body_lines: [{"t": text, "p": page, "h": font height}]
    footnotes:  {"12": "text of note 12"}"""
    sizes = collections.Counter()
    marked = collections.Counter()
    for pg in pages:
        for l in pg["lines"]:
            sizes[round(l["h"])] += len(l["t"])
            if note_start(l, _clean_line(l["t"])):
                marked[round(l["h"])] += 1
    total = sum(sizes.values()) or 1
    body_h = sizes.most_common(1)[0][0] if sizes else 0
    # Footnotes are set smaller than the body, sometimes in two sizes, sometimes only 1pt smaller,
    # and in a short law with long notes they are the most used size. So: the body size is the
    # most used size above the smallest size that has numbered notes, and every numbered-note
    # size below the body is a footnote size.
    note_h = 0
    small = min(marked) if marked else 0
    above = {s2: c for s2, c in sizes.items() if s2 > small}
    if small and above and sum(above.values()) / total >= 0.2:
        body_h = max(above, key=above.get)
        note_h = max(h for h in marked if h < body_h)
    exact = collections.Counter()
    for pg in pages:
        for l in pg["lines"]:
            if round(l["h"]) == body_h:
                exact[l["h"]] += len(l["t"])
    body_exact = exact.most_common(1)[0][0] if exact else body_h
    # for each possible note opening, the number of the possible opening that comes after it
    nxt_of: dict[int, int] = {}
    if note_h:
        prev_line = None
        for pg in pages:
            for l in sorted(pg["lines"], key=lambda l: (l.get("o", 0), -l["y"])):
                if l.get("mark"):
                    n = l["mark"][0]
                else:
                    t = _clean_line(l["t"])
                    m = None if PAGE_NO.match(t) else (_NOTE_A.match(t) or _NOTE_B.match(t))
                    if not m:
                        continue
                    n = int(m.group(1))
                if prev_line is not None:
                    nxt_of[prev_line] = n
                prev_line = id(l)
    body: list[dict] = []
    notes: dict[str, str] = {}
    cur_note: str | None = None
    aliases: dict[str, str] = {}      # mark 14 -> note 13 when the file prints "13-14" before one note
    last_n = 0
    prev_page_had_notes = False
    n_text_chars = 0
    for pg in pages:
        # lines top-to-bottom
        lines = sorted(pg["lines"], key=lambda l: (l.get("o", 0), -l["y"]))
        # footnote zone = the run of note-size lines that ends the page (page number aside)
        start = len(lines)
        if note_h:
            i = len(lines) - 1
            while i >= 0:
                t = _clean_line(lines[i]["t"])
                if not t or PAGE_NO.match(t):
                    i -= 1
                    continue
                if round(lines[i]["h"]) <= note_h:
                    start = i
                    i -= 1
                    continue
                if lines[i]["h"] <= body_exact - 0.3:
                    i -= 1          # a shade smaller than the body (quotations inside a note):
                    continue        # in the notes only if note-size lines sit above it
                # a body-size line. It still belongs to the notes when it is part of a note the
                # file prints at body size: a few lines opening with "12 - ", right under note lines
                j, seen, opens = i, 0, False
                while j >= 0 and seen < 6:
                    tj = _clean_line(lines[j]["t"])
                    if not tj or PAGE_NO.match(tj):
                        j -= 1
                        continue
                    if round(lines[j]["h"]) <= note_h:
                        break
                    seen += 1
                    m = _NOTE_A.match(tj)
                    if m and int(m.group(1)) > last_n:
                        k = j - 1
                        while k >= 0 and (not _clean_line(lines[k]["t"]) or PAGE_NO.match(_clean_line(lines[k]["t"]))):
                            k -= 1
                        opens = k >= 0 and round(lines[k]["h"]) <= note_h
                        break
                    j -= 1
                if not opens:
                    break
                start = j
                i = j - 1
            # it opens with a numbered note, or continues the note of the previous page
            while start < len(lines):
                t = _clean_line(lines[start]["t"])
                if note_start(lines[start], t, last_n, nxt=nxt_of.get(id(lines[start]))) or (prev_page_had_notes and cur_note):
                    break
                start += 1
        had = False
        zone_lines = 0
        for i, l in enumerate(lines):
            t = _clean_line(l["t"])
            if not t or PAGE_NO.match(t):
                continue
            n_text_chars += len(t)
            if i >= start:
                had = True
                prev_text = notes[cur_note] if cur_note and (zone_lines or not prev_page_had_notes) else ""
                m = note_start(l, t, last_n, after_stop=not zone_lines or prev_text.rstrip().endswith(_SENTENCE_END),
                               nxt=nxt_of.get(id(l)))
                zone_lines += 1
                if m and m[0][0] not in notes:
                    cur_note = m[0][0]
                    last_n = int(m[0][-1])
                    notes[cur_note] = m[1]
                    for extra in m[0][1:]:
                        aliases[extra] = cur_note
                else:
                    notes[cur_note] += "\n" + t      # continuation, possibly from the previous page
                continue
            body.append({"t": t, "p": pg["p"], "h": l["h"], "x0": l["x0"], "x1": l["x1"]})
        prev_page_had_notes = had
    for extra, main in aliases.items():
        notes.setdefault(extra, notes[main])
    nums = sorted(int(k) for k in notes)
    gaps = [n for n in range(1, nums[-1] + 1) if str(n) not in notes] if nums else []
    return body, notes, {"body_font": body_h, "note_font": note_h, "chars": n_text_chars, "footnotes": len(notes),
                         "footnote_numbers_missing": gaps}


def extract(pdf_path: str) -> tuple[list[dict], dict[str, str], dict]:
    pages, meta = read_pages(pdf_path)
    body, notes, stats = split_body_footnotes(pages)
    meta.update(stats)
    return body, notes, meta


def to_text(body: list[dict], notes: dict[str, str]) -> str:
    out = [l["t"] for l in body]
    if notes:
        out += ["", "-" * 20]
        out += [f"[^{k}]: {v}" for k, v in notes.items()]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    b, n, meta = extract(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        fh.write(to_text(b, n))
    print(meta)
