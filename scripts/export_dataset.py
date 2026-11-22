#!/usr/bin/env python3
"""Export every article as one JSON line, for any AI tool, search index or RAG pipeline.

    python3 scripts/export_dataset.py        # writes exports/moroccan-law-articles.jsonl.gz

One record per article:
  id            "<text>:<article>"            stable identifier ("#2" added when the source repeats a number)
  text, skill   text identifier and skill folder
  law           title of the law (Arabic), law_fr (French title)
  article       article number as printed ("65-1", "85 مكرر"); heading; path (book › title › chapter)
  body          official text of the article (Arabic, or French for the -fr versions)
  footnotes     the source's footnotes cited in the article (amending laws, Bulletin officiel)
  language      "ar" | "fr"
  version_date  consolidation date printed in the PDF, when there is one
  source_url    the official PDF on adala.justice.gov.ma; source_sha256 its checksum
  reviewed      true for the 95 texts reviewed one by one, false for the extended corpus
Standard library only.
"""
import glob
import gzip
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import law  # noqa: E402

NOTE = re.compile(r"^\[\^(\d+)\]:\s*(.*)$", re.M)


def main() -> int:
    out_path = os.path.join(REPO, "exports", "moroccan-law-articles.jsonl.gz")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    n_texts = n_arts = 0
    with gzip.open(out_path, "wt", encoding="utf-8") as out:
        for meta_path in sorted(glob.glob(os.path.join(REPO, "skills", "*", "references", "*", "meta.json"))):
            skill = meta_path.split(os.sep)[-4]
            slug = meta_path.split(os.sep)[-2]
            m = json.load(open(meta_path, encoding="utf-8"))
            law.ROOT = os.path.dirname(os.path.dirname(meta_path))
            n_texts += 1
            seen: dict[str, int] = {}
            for a in law.load_articles(slug):
                seen[a["num"]] = seen.get(a["num"], 0) + 1
                uid = f"{slug}:{a['num']}" + (f"#{seen[a['num']]}" if seen[a["num"]] > 1 else "")
                notes = {k: v.strip() for k, v in NOTE.findall(a["body"])}
                body = NOTE.sub("", a["body"]).strip()
                rec = {"id": uid, "text": slug, "skill": skill,
                       "law": m.get("title"), "law_fr": m.get("title_fr"),
                       "article": a["num"], "heading": a["heading"], "path": a["path"],
                       "body": body, "footnotes": notes, "language": m.get("language", "ar"),
                       "version_date": m.get("consolidated_on"), "source_url": m.get("source_url"),
                       "source_sha256": m.get("pdf_sha256"), "reviewed": skill != "maroc-corpus"}
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_arts += 1
    print(f"{n_arts} articles from {n_texts} texts -> {os.path.relpath(out_path, REPO)} "
          f"({os.path.getsize(out_path) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
