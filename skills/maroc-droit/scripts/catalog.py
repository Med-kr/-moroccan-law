#!/usr/bin/env python3
"""Search the catalog of every legal text published on Adala (Moroccan Ministry
of Justice) and download the official PDF of any of them. Standard library only.

    catalog.py search <words> [--lang ar|fr] [--type T] [--max N] [--any]
    catalog.py show <id>              full record of one text
    catalog.py get <id> [--out DIR]   download the official PDF, print its local path
    catalog.py stats                  what the catalog contains and when it was built

Search matches the title, the law number and the folder path. Arabic matching
ignores hamza / ta-marbuta / diacritics; French matching ignores accents and case.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references")
BASE = "https://adala.justice.gov.ma/api/"
UA = "moroccan-law-skills/0.1 (open-source legal reference tool)"


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load() -> tuple[dict, list[dict]]:
    with open(os.path.join(ROOT, "catalog-meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    rows = []
    with open(os.path.join(ROOT, "catalog.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return meta, rows


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[ـ]", "", s)
    s = re.sub(r"[أإآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"(\d)[-.](\d)", r"\1.\2", s)          # 65-99 and 65.99 are the same law number
    return s.lower()


def url(row: dict) -> str:
    return BASE + urllib.parse.quote(row["path"])


def line(row: dict) -> str:
    bits = [str(row["id"]), row["lang"], (row.get("updated") or "")[:10], row.get("type") or "-", row["title"]]
    return "\t".join(bits) + f"\n\t↳ {' / '.join(row['folder'])}"


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    meta, rows = load()
    by_id = {str(r["id"]): r for r in rows}
    if cmd == "stats":
        print(json.dumps(meta, ensure_ascii=False, indent=1))
    elif cmd == "search" and rest:
        lang = typ = None
        limit, any_, words = 20, False, []
        i = 0
        while i < len(rest):
            if rest[i] == "--lang" and i + 1 < len(rest):
                lang = rest[i + 1]; i += 2
            elif rest[i] == "--type" and i + 1 < len(rest):
                typ = norm(rest[i + 1]); i += 2
            elif rest[i] == "--max" and i + 1 < len(rest):
                limit = int(rest[i + 1]); i += 2
            elif rest[i] == "--any":
                any_ = True; i += 1
            else:
                words.extend(norm(w) for w in rest[i].split()); i += 1    # a quoted phrase is several words
        hits = []
        for r in rows:
            if lang and r["lang"] != lang:
                continue
            if typ and typ not in norm(r.get("type") or ""):
                continue
            hay = norm(" ".join([r["title"], r.get("number") or "", r.get("related") or "", " ".join(r["folder"]), os.path.basename(r["path"])]))
            if (any if any_ else all)(w in hay for w in words):
                hits.append(r)
        hits.sort(key=lambda r: r.get("updated") or "", reverse=True)
        if not hits:
            die("no text matches. Try fewer words, the law number (e.g. 65.99), the other language, or --any.", 3)
        print(f"{len(hits)} result(s); catalog built {meta['generated_at'][:10]}. Columns: id, lang, updated on Adala, type, title")
        for r in hits[:limit]:
            print(line(r))
        if len(hits) > limit:
            print(f"(+{len(hits) - limit} more: use --max)")
    elif cmd == "show" and rest:
        r = by_id.get(rest[0]) or die(f"no text with id {rest[0]}", 3)
        print(json.dumps({**r, "url": url(r)}, ensure_ascii=False, indent=1))
    elif cmd == "get" and rest:
        r = by_id.get(rest[0]) or die(f"no text with id {rest[0]}", 3)
        out = os.path.expanduser("~/.cache/moroccan-law-skills")
        if "--out" in rest:
            out = rest[rest.index("--out") + 1]
        os.makedirs(out, exist_ok=True)
        dest = os.path.join(out, f"adala-{r['id']}.pdf")
        if not os.path.exists(dest):
            req = urllib.request.Request(url(r), headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = resp.read()
            except Exception as exc:
                die(f"download failed ({exc}). The file may have been replaced on Adala; open {url(r)} or search again.", 4)
            if not data.startswith(b"%PDF"):
                die("the server did not return a PDF; the file may have been replaced on Adala.", 4)
            with open(dest, "wb") as fh:
                fh.write(data)
        print(dest)
        print(f"title: {r['title']}\nupdated on Adala: {(r.get('updated') or '')[:10]}\nsource: {url(r)}")
    else:
        die(__doc__, 2)


if __name__ == "__main__":
    main(sys.argv[1:])
