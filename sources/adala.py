#!/usr/bin/env python3
"""Build a catalog of legal texts published on Adala (adala.justice.gov.ma),
the legal portal of the Moroccan Ministry of Justice.

Walks the public resource folders (Arabic and French trees) and writes one
JSON catalog with every folder and every file (metadata only, no PDF download).

Usage:
    python3 sources/adala.py --out data/catalog.json
    python3 sources/adala.py --roots ar:1 fr:338 --delay 0.4

Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://adala.justice.gov.ma"
UA = "moroccan-law-skills-catalog/0.1 (open-source legal reference tool)"
DEFAULT_ROOTS = ["ar:1", "fr:338"]


def fetch(url: str, retries: int = 3, timeout: int = 60) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def build_id() -> str:
    html = fetch(BASE + "/").decode("utf-8", "replace")
    m = re.search(r'"buildId":"([^"]+)"', html)
    if not m:
        raise RuntimeError("could not find Next.js buildId on the Adala home page")
    return m.group(1)


def folder_json(bid: str, locale: str, folder_id: int) -> dict:
    url = f"{BASE}/_next/data/{bid}/{locale}/resources/{folder_id}.json?resourceId={folder_id}"
    data = json.loads(fetch(url).decode("utf-8"))
    return data["pageProps"]["content"]


def file_url(path: str | None) -> str | None:
    if not path:
        return None
    return BASE + "/api/" + urllib.parse.quote(path)


def simplify_file(entry: dict, locale: str, crumbs: list[str], folder_id: int) -> dict:
    """Flatten one file record. Adala nests the stored file under `File`
    (or the record itself is the file, depending on the listing)."""
    f = entry.get("File") or entry.get("file") or {}
    path = f.get("path") or entry.get("path")
    return {
        "id": entry.get("id"),
        "locale": locale,
        "folder_id": folder_id,
        "breadcrumbs": crumbs,
        "title": (entry.get("title") or f.get("name") or entry.get("name") or "").strip(),
        "object": entry.get("object"),
        "law_number": entry.get("lawNumber"),
        "law_type": (entry.get("LawType") or {}).get("name"),
        "theme": (entry.get("theme") or {}).get("name"),
        "gregorian_date": entry.get("gregorianDate"),
        "publishing_date": entry.get("publishingDate"),
        "updated_at": entry.get("updatedAt") or f.get("updatedAt"),
        "related": entry.get("related"),
        "keywords": entry.get("keywords"),
        "path": path,
        "url": file_url(path),
    }


def crawl(bid: str, locale: str, root: int, delay: float, log) -> tuple[list[dict], list[dict]]:
    folders: list[dict] = []
    files: list[dict] = []
    seen: set[int] = set()
    stack: list[tuple[int, list[str]]] = [(root, [])]
    while stack:
        fid, crumbs = stack.pop()
        if fid in seen:
            continue
        seen.add(fid)
        try:
            c = folder_json(bid, locale, fid)
        except Exception as exc:  # keep going, report at the end
            log(f"  ! folder {fid}: {exc}")
            folders.append({"id": fid, "locale": locale, "error": str(exc), "breadcrumbs": crumbs})
            continue
        name = (c.get("name") or "").strip()
        here = crumbs + [name]
        raw_files = list(c.get("files") or []) + list(c.get("FileFolders") or [])
        folders.append({
            "id": fid,
            "locale": locale,
            "name": name,
            "parent_id": c.get("parentId"),
            "breadcrumbs": here,
            "updated_at": c.get("updatedAt"),
            "n_files": len(raw_files),
            "n_subfolders": len(c.get("folders") or []),
        })
        for entry in raw_files:
            files.append(simplify_file(entry, locale, here, fid))
        log(f"  {locale} {fid:>5} files={len(raw_files):<4} sub={len(c.get('folders') or []):<3} {' / '.join(here)}")
        for sub in c.get("folders") or []:
            stack.append((sub["id"], here))
        time.sleep(delay)
    return folders, files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/catalog.json")
    ap.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS, help="locale:folderId pairs")
    ap.add_argument("--delay", type=float, default=0.3, help="seconds between requests")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    log = (lambda *_: None) if args.quiet else (lambda s: print(s, file=sys.stderr))
    bid = build_id()
    log(f"buildId {bid}")
    all_folders: list[dict] = []
    all_files: list[dict] = []
    for spec in args.roots:
        locale, _, rid = spec.partition(":")
        fo, fi = crawl(bid, locale, int(rid), args.delay, log)
        all_folders += fo
        all_files += fi
    catalog = {
        "source": BASE,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "roots": args.roots,
        "n_folders": len(all_folders),
        "n_files": len(all_files),
        "folders": all_folders,
        "files": all_files,
    }
    import os
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=1)
    errors = [f for f in all_folders if "error" in f]
    print(f"folders={len(all_folders)} files={len(all_files)} errors={len(errors)} -> {args.out}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
