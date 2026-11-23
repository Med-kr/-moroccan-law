#!/usr/bin/env python3
"""Build the skills from the official PDFs listed in skills.json.

For every text: download the PDF from Adala (cached), extract and parse it,
then write  skills/<skill>/references/<slug>/{text.md,toc.md,meta.json}.
Also installs the lookup tool into each skill and renders SKILL.md.

    uv run --with pymupdf python scripts/build.py            # build everything
    uv run --with pymupdf python scripts/build.py --only maroc-travail
    uv run --with pymupdf python scripts/build.py --check    # only report texts whose source changed
    python3 scripts/build.py --render-only                   # re-render SKILL.md / tools / catalog, no PDF work

    uv run --with pymupdf python scripts/build.py --country ma   # which countries/<code>/ to build

Needs the country's catalog (for Morocco: run sources/adala.py first). A text can also be
listed with a direct "url" instead of a catalog "id", so a country needs no crawler to start.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CACHE = os.path.join(REPO, ".cache", "pdf")
UA = "moroccan-law-skills-build/0.1 (open-source legal reference tool)"


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def download(entry: dict) -> str:
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1(entry["path"].encode("utf-8")).hexdigest()[:12]
    dest = os.path.join(CACHE, f"{entry['id']}-{key}.pdf")
    if not os.path.exists(dest):
        req = urllib.request.Request(entry["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=180) as resp, open(dest + ".part", "wb") as out:
            shutil.copyfileobj(resp, out)
        os.replace(dest + ".part", dest)
    return dest


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


COUNTRY: dict = {}        # countries/<code>/country.json of the build in progress

LABELS = {
    "ar": {"source": "المصدر الرسمي", "version": "صيغة محينة بتاريخ", "none": "غير مذكور في النص",
           "notice": "نص مستخرج آليا من ملف PDF المنشور على بوابة عدالة (وزارة العدل). المرجع عند الاختلاف هو الجريدة الرسمية.",
           "header": "ديباجة ومعطيات النشر", "toc": "فهرس", "before": "ظهير الإصدار / مواد تمهيدية",
           "after": "ملحق / مواد ختامية", "body": "المتن",
           "orphans": "هوامش لم يُعثر على موضع إحالتها في النص"},
    "fr": {"source": "Source officielle", "version": "Version consolidée du", "none": "non indiquée dans le texte",
           "notice": "Texte extrait automatiquement du PDF publié sur le portail Adala (ministère de la Justice). "
                     "Version française : elle peut être antérieure à la version arabe, qui seule fait foi avec le Bulletin officiel.",
           "header": "Préambule et données de publication", "toc": "Sommaire", "before": "Dahir de promulgation / articles préliminaires",
           "after": "Annexe / dispositions finales", "body": "Texte",
           "orphans": "Notes dont l'appel n'a pas été retrouvé dans le texte"},
}


def render_text(cfg: dict, entry: dict, parsed: dict) -> tuple[str, str]:
    kw = parsed["article_keyword"]
    L = dict(LABELS[parsed.get("lang", "ar")])
    L["notice"] = COUNTRY.get("source", {}).get("notice_" + parsed.get("lang", "ar"), L["notice"])
    title = cfg["fr"] if parsed.get("lang") == "fr" else cfg["ar"]
    out: list[str] = [f"# {title}", ""]
    out += [f"> {L['source']}: {entry['url']}",
            f"> {L['version']}: {parsed['consolidated_on'] or L['none']}",
            f"> {L['notice']}",
            ""]
    if parsed["header"]:
        out += [f"# {L['header']}", ""] + parsed["header"] + [""]
        if parsed.get("header_notes"):
            out += [f"[^{k}]: {v}" for k, v in parsed["header_notes"].items()] + [""]
    toc: list[str] = [f"# {L['toc']} — {title}", ""]
    main = parsed["main_part"]
    for pi, part in enumerate(parsed["parts"]):
        if pi != main:
            label = L["before"] if pi < main else L["after"]
            out += [f"# {label}", ""]
            side_path: list[str] | None = None
            for a in part:
                if a["path"] and a["path"] != side_path:
                    out += [f"> § {' › '.join(a['path'])}", ""]
                side_path = a["path"]
                out += ([f"### {a['heading']}", ""] if a["heading"] else []) + [a["text"], ""]
                for k, v in a["notes"].items():
                    out.append(f"[^{k}]: {v}")
                out.append("")
            continue
        out += [f"# {L['body']}", ""]
        last_path: list[str] | None = None
        toc_open: dict | None = None

        def close_toc():
            if toc_open:
                rng = toc_open["first"] if toc_open["first"] == toc_open["last"] else f"{toc_open['first']} – {toc_open['last']}"
                toc.append(f"{'  ' * toc_open['depth']}- {toc_open['title']} ({kw} {rng})")

        for a in part:
            if a["path"] != last_path:
                close_toc()
                # print the titles of levels that changed
                common = 0
                if last_path:
                    while common < min(len(last_path), len(a["path"])) and last_path[common] == a["path"][common]:
                        common += 1
                for d in range(common, len(a["path"]) - 1):
                    toc.append(f"{'  ' * d}- {a['path'][d]}")
                if a["path"]:
                    out += [f"> § {' › '.join(a['path'])}", ""]
                    toc_open = {"title": a["path"][-1], "depth": len(a["path"]) - 1, "first": a["num"], "last": a["num"]}
                else:
                    toc_open = None
                last_path = a["path"]
            if a.get("block"):
                out += [a["text"], ""]
                for k, v in a["notes"].items():
                    out.append(f"[^{k}]: {v}")
                continue
            if toc_open:
                toc_open["last"] = a["num"]
                if not toc_open["first"]:
                    toc_open["first"] = a["num"]
            out += [f"## {a['heading']}", "", a["text"], ""]
            for k, v in a["notes"].items():
                out.append(f"[^{k}]: {v}")
            if a["notes"]:
                out.append("")
        close_toc()
    if parsed.get("orphan_notes"):
        out += ["", f"# {L['orphans']}", ""] + [f"[^{k}]: {v}" for k, v in parsed["orphan_notes"].items()]
    return "\n".join(out).rstrip() + "\n", "\n".join(toc).rstrip() + "\n"


# Some source files print a dahir or decree number back to front ("ظهير شريف رقم 11.03.1" for
# 1.11.03): the three groups of a left-to-right number laid out right-to-left. A dahir number
# always starts with "1." and a decree number with "2.", so the printed form is unambiguous
# and is put back in order. Counted in meta.json ("source_numbers_reordered").
DAHIR_REVERSED = re.compile(r"((?:ظهير|الظهير|مرسوم|المرسوم)(?:\s+\S+){0,4}?\s+رقم\s+)(\d{2})\.(\d{2,3})\.([12])(?![\d.])")


# The conjunction « أو » typed without the space before the next word in the source documents
# (« أومن ينوب عنه », « أوفي القطاع العام », « أوعن طريق »): every case read in context is
# « أو » + a word. The space is put back; meta.json counts it ("source_spaces_restored").
OR_GLUED = re.compile(r"(?<![\u0621-\u064A])أو(?=(?:في|من|عن)(?![\u0621-\u064A]))")


def apply_errata(slug: str, body: list[dict]) -> list[dict]:
    """Documented corrections of errors printed in the official file itself
    (countries/<code>/errata.json). Each one replaces one exact line; every correction applied
    is listed in meta.json ("source_corrections") with its reason, and one that no longer
    matches stops the build, so that a corrected source file is noticed."""
    path = os.path.join(REPO, "countries", COUNTRY.get("_code", "ma"), "errata.json")
    todo = [e for e in (load_json(path) if os.path.exists(path) else []) if e["slug"] == slug]
    done = []
    for e in todo:
        hits = [l for l in body if l["t"] == e["line"] and (not e.get("page") or l["p"] == e["page"])]
        if len(hits) != 1:
            raise RuntimeError(f"erratum for {slug} matches {len(hits)} lines (expected 1): {e['line']!r}")
        hits[0]["t"] = e["replace"]
        done.append({k: e[k] for k in ("page", "line", "replace", "why") if k in e})
    return done


def article_notes(slug: str) -> dict:
    """Warnings attached to an article (countries/<code>/article_notes.json), shown by law.py
    under the article: divergences between official versions and the like."""
    path = os.path.join(REPO, "countries", COUNTRY.get("_code", "ma"), "article_notes.json")
    return {e["article"]: e["note"] for e in (load_json(path) if os.path.exists(path) else []) if slug in e["slugs"]}


def build_text(skill_dir: str, cfg: dict, entry: dict) -> dict:
    import lawparse
    import pdf_text
    pdf = download(entry)
    body, notes, meta = pdf_text.extract(pdf)
    corrections = apply_errata(cfg["slug"], body)
    parsed = lawparse.parse(body, notes)
    text_md, toc_md = render_text(cfg, entry, parsed)
    text_md, n_dahir = DAHIR_REVERSED.subn(r"\1\4.\2.\3", text_md)
    text_md, n_spaces = OR_GLUED.subn("أو ", text_md)
    # "mathematical" digits (𝟎𝟏𝟐, U+1D7CE-1D7FF) used as ordinary digits in some source files
    text_md = "".join(chr(0x30 + (ord(c) - 0x1D7CE) % 10) if 0x1D7CE <= ord(c) <= 0x1D7FF else c for c in text_md)
    ref = os.path.join(skill_dir, "references", cfg["slug"])
    os.makedirs(ref, exist_ok=True)
    with open(os.path.join(ref, "text.md"), "w", encoding="utf-8") as fh:
        fh.write(text_md)
    with open(os.path.join(ref, "toc.md"), "w", encoding="utf-8") as fh:
        fh.write(toc_md)
    info = {
        "slug": cfg["slug"],
        "title": cfg["ar"],
        "title_fr": cfg["fr"],
        "source_title": entry["title"],
        "source_id": entry["id"],
        "source_name": COUNTRY.get("source", {}).get("name", ""),
        "source_url": entry["url"],
        "source_path": entry["path"],
        "source_updated_at": entry.get("updated_at"),
        "consolidated_on": parsed["consolidated_on"],
        "pdf_sha256": sha256(pdf),
        "pdf_pages": meta["pages"],
        "extracted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "article_keyword": parsed["article_keyword"],
        "n_articles": parsed["n_articles"],
        "n_footnotes": len(notes),
        "n_footnotes_unplaced": len(parsed.get("orphan_notes", {})),
        "footnote_numbers_missing": meta.get("footnote_numbers_missing", []),
        "glyph_fixes": meta.get("glyph_fixes", []),
        "source_numbers_reordered": n_dahir,
        "source_corrections": corrections,
        "source_spaces_restored": n_spaces,
        "article_notes": article_notes(cfg["slug"]),
        "other_parts": [len(p) for i, p in enumerate(parsed["parts"]) if i != parsed["main_part"]],
        "anomalies": parsed["anomalies"],
        "language": parsed.get("lang", "ar"),
    }
    with open(os.path.join(ref, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=1)
    return info


def render_skill_md(skill: dict, infos: list[dict], template: str) -> str:
    rows = []
    for i in infos:
        rows.append(f"| `{i['slug']}` | {i['title']} | {i['title_fr']} | {i['n_articles']} {i['article_keyword']} | {i['consolidated_on'] or '—'} | {(i['source_updated_at'] or '')[:10]} |")
    table = "\n".join(["| text | النص | Texte | حجم | صيغة محينة بتاريخ | source |", "|---|---|---|---|---|---|"] + rows)
    return (template
            .replace("{{name}}", skill["name"])
            .replace("{{title_ar}}", skill["title_ar"])
            .replace("{{title_fr}}", skill["title_fr"])
            .replace("{{keywords}}", skill["keywords"])
            .replace("{{texts_table}}", table)
            .replace("{{built_on}}", dt.date.today().isoformat()))


def write_catalog(skill_dir: str, catalog: dict, config: dict, md: str) -> str:
    """Ship a compact copy of the Adala catalog with the general skill."""
    ref = os.path.join(skill_dir, "references")
    os.makedirs(ref, exist_ok=True)
    rows = []
    seen = set()
    for f in catalog["files"]:
        if not f.get("id") or not f.get("path") or (f["id"], f["locale"]) in seen:
            continue
        seen.add((f["id"], f["locale"]))
        rows.append({"id": f["id"], "lang": f["locale"], "title": re.sub(r"\s+", " ", f["title"]).strip(),
                     "type": f.get("law_type"), "number": f.get("law_number"), "related": f.get("related"),
                     "updated": f.get("updated_at"), "folder": [b.strip() for b in f["breadcrumbs"] if b.strip()],
                     "path": f["path"]})
    with open(os.path.join(ref, "catalog.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({k: v for k, v in r.items() if v}, ensure_ascii=False) + "\n")
    n_ar = sum(1 for r in rows if r["lang"] == "ar")
    meta = {"source": catalog["source"], "generated_at": catalog["generated_at"], "n_texts": len(rows),
            "n_ar": n_ar, "n_fr": len(rows) - n_ar}
    with open(os.path.join(ref, "catalog-meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    shutil.copyfile(os.path.join(REPO, "tools", "catalog.py"), os.path.join(skill_dir, "scripts", "catalog.py"))
    table = "\n".join(f"| `{sk['name']}` | {sk['title_fr']} — {sk['title_ar']} |" for sk in config["skills"] if not sk.get("router"))
    return (md.replace("{{n_catalog}}", str(len(rows))).replace("{{n_ar}}", str(n_ar))
              .replace("{{n_fr}}", str(len(rows) - n_ar)).replace("{{catalog_date}}", catalog["generated_at"][:10])
              .replace("{{skills_table}}", table))


_HIJRI = ("محرم|صفر|ربيع الأول|ربيع الاول|ربيع الآخر|ربيع الثاني|جمادى الأولى|جمادى الاولى|جمادى الآخرة|جمادى الثانية|"
          "رجب|شعبان|رمضان|شوال|ذي القعدة|ذو القعدة|ذي الحجة|ذو الحجة")
_GREG = "يناير|فبراير|مارس|أبريل|ابريل|ماي|مايو|يونيو|يوليو|يوليوز|غشت|أغسطس|شتنبر|سبتمبر|أكتوبر|نونبر|نوفمبر|دجنبر|ديسمبر"
DATE = re.compile(rf"(\d{{1,3}})\s*(?:من\s+)?({_HIJRI}|{_GREG})\s+(\d{{2,4}})")


def impossible_dates(text: str) -> list[str]:
    """Dates no calendar has (day 62, Hijri year 8242, Gregorian year 2222): the sign of a font
    whose digits are mapped to other digits. One or two are typos of the source; many are not."""
    out = []
    for d, mo, y in DATE.findall(text):
        d, y = int(d), int(y)
        hijri = re.fullmatch(_HIJRI, mo) is not None
        if not 1 <= d <= 31 or (hijri and not 1300 <= y <= 1460) or (not hijri and not 1900 <= y <= 2030):
            out.append(f"{d} {mo} {y}")
    return out


DIGIT_IN_WORD = re.compile(r"[\u0621-\u064A]+[0-9]+[\u0621-\u064A]+")


def quality_gate(skill_dir: str, slug: str, info: dict) -> str | None:
    """Extended corpus only: reasons not to ship a text built without review, or None."""
    text = open(os.path.join(skill_dir, "references", slug, "text.md"), encoding="utf-8").read()
    words = max(1, len(text.split()))
    if info["n_articles"] < 1:
        return "no article found"
    if len(text) < 400:
        return "almost no text (scanned or empty PDF)"
    digits = len(DIGIT_IN_WORD.findall(text))
    if digits * 10000 / words > 10:
        return f"font maps letters to digits ({digits} words such as « م6رر »)"
    if len(info["anomalies"]) > 5 + 0.25 * info["n_articles"]:
        return f"structure not recovered ({len(info['anomalies'])} parser notes for {info['n_articles']} articles)"
    bad_dates = impossible_dates(text)
    if len(bad_dates) >= 3:
        return f"digits garbled by the font ({len(bad_dates)} impossible dates such as « {bad_dates[0]} »)"
    if info.get("glyph_fixes") and len(info["glyph_fixes"]) > 3:
        return "too many wrong letters in the fonts"
    for bad in ("خالل", "أعاله", "اإل", "األ", "اآل"):
        if bad in text:
            return f"lam-alef ligature not repaired (« {bad} »)"
    if re.search(r"[\uE000-\uF8FF\uFFFD]", text):
        return "private-use or replacement characters in the text"
    nums = re.findall(r"^## (?:المادة|الفصل) (.+?)(?::.*)?$", text, re.M)
    if len(nums) - len(set(nums)) > max(2, len(nums) // 100):
        return f"{len(nums) - len(set(nums))} duplicate article headings"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="skill names to build")
    ap.add_argument("--shard", help="I/N: extended-corpus worker; builds texts I, I+N, ... from the end, "
                                    "writes no SKILL.md or report (run the normal build afterwards)")
    ap.add_argument("--check", action="store_true", help="report texts whose source file changed since the last build")
    ap.add_argument("--render-only", action="store_true",
                    help="no PDF work: re-render SKILL.md, tools and the catalog from the texts already built")
    ap.add_argument("--country", default="ma", help="folder under countries/ (default: ma)")
    args = ap.parse_args()

    COUNTRY.update(load_json(os.path.join(REPO, "countries", args.country, "country.json")))
    COUNTRY["_code"] = args.country
    cat_path = os.path.join(REPO, COUNTRY.get("catalog") or "")
    catalog = load_json(cat_path) if COUNTRY.get("catalog") and os.path.exists(cat_path) else \
        {"source": COUNTRY.get("source", {}).get("url", ""), "generated_at": "", "files": []}
    by_id = {f["id"]: f for f in catalog["files"] if f.get("id") and f.get("url")}
    config = load_json(os.path.join(REPO, COUNTRY["skills"]))
    tdir = os.path.join(REPO, COUNTRY["templates"])
    template = open(os.path.join(tdir, "SKILL.md.tmpl"), encoding="utf-8").read()
    router_template = open(os.path.join(tdir, "ROUTER.md.tmpl"), encoding="utf-8").read()

    report = []
    excluded: list[dict] = []
    changed = 0
    for skill in config["skills"]:
        if args.only and skill["name"] not in args.only:
            continue
        skill_dir = os.path.join(REPO, "skills", skill["name"])
        infos = []
        todo = skill["texts"]
        if args.shard:
            if not skill.get("auto"):
                continue
            i_, n_ = (int(x) for x in args.shard.split("/"))
            todo = [t for k, t in enumerate(todo) if k % n_ == i_][::-1]
        for cfg in todo:
            entry = by_id.get(cfg.get("id"))
            if entry is None and cfg.get("url"):      # text listed by direct URL, no catalog needed
                entry = {"id": cfg["slug"], "url": cfg["url"], "path": cfg["url"], "title": cfg.get("ar") or cfg.get("fr"),
                         "updated_at": cfg.get("updated_at")}
            meta_path = os.path.join(skill_dir, "references", cfg["slug"], "meta.json")
            if entry is None:
                print(f"!! {skill['name']}/{cfg['slug']}: id {cfg.get('id')} is no longer in the catalog (repealed or moved?)")
                changed += 1
                continue
            if args.check:
                old = load_json(meta_path) if os.path.exists(meta_path) else None
                if old is None:
                    print(f"NEW      {skill['name']}/{cfg['slug']}")
                    changed += 1
                elif old["source_path"] != entry["path"]:
                    print(f"CHANGED  {skill['name']}/{cfg['slug']}  (new file published on Adala, updated {(entry.get('updated_at') or '')[:10]})")
                    changed += 1
                continue
            if args.render_only:
                if os.path.exists(meta_path):
                    infos.append(load_json(meta_path))
                continue
            if skill.get("auto") and os.path.exists(meta_path) and load_json(meta_path).get("source_path") == entry["path"]:
                infos.append(load_json(meta_path))          # extended corpus: already built from this file
                continue
            try:
                info = build_text(skill_dir, cfg, entry)
            except Exception as exc:
                print(f"!! {skill['name']}/{cfg['slug']}: {type(exc).__name__}: {exc}")
                report.append({"skill": skill["name"], "slug": cfg["slug"], "error": str(exc)})
                if skill.get("auto"):
                    excluded.append({"slug": cfg["slug"], "id": cfg["id"], "title": cfg["ar"], "reason": f"error: {exc}"[:200]})
                continue
            if skill.get("auto"):
                why = quality_gate(skill_dir, cfg["slug"], info)
                if why:
                    shutil.rmtree(os.path.join(skill_dir, "references", cfg["slug"]), ignore_errors=True)
                    excluded.append({"slug": cfg["slug"], "id": cfg["id"], "title": cfg["ar"], "reason": why})
                    print(f"-- {skill['name']}/{cfg['slug']}: excluded ({why})")
                    continue
            infos.append(info)
            report.append({"skill": skill["name"], **{k: info[k] for k in ("slug", "n_articles", "article_keyword", "consolidated_on", "n_footnotes", "other_parts", "anomalies", "pdf_pages")}})
            print(f"ok {skill['name']}/{cfg['slug']}: {info['n_articles']} {info['article_keyword']}, "
                  f"{info['pdf_pages']} p, version {info['consolidated_on']}, anomalies {len(info['anomalies'])}")
        if args.check or args.shard or not infos:
            continue
        os.makedirs(os.path.join(skill_dir, "scripts"), exist_ok=True)
        shutil.copyfile(os.path.join(REPO, "tools", "law.py"), os.path.join(skill_dir, "scripts", "law.py"))
        shutil.copyfile(os.path.join(REPO, "tools", "cards.py"), os.path.join(skill_dir, "scripts", "cards.py"))
        tmpl = router_template if skill.get("router") else template
        if skill.get("template"):
            tmpl = open(os.path.join(REPO, "countries", COUNTRY.get("_code", "ma"), "templates", skill["template"]),
                        encoding="utf-8").read()
        md = render_skill_md(skill, infos, tmpl)
        md = md.replace("{{n_texts}}", str(len(infos))).replace(
            "{{n_articles}}", f"{sum(i['n_articles'] for i in infos):,}")
        for tool in skill.get("tools", []):           # extra command-line tools of this skill
            shutil.copyfile(os.path.join(REPO, "tools", tool), os.path.join(skill_dir, "scripts", tool))
        if skill.get("extra"):                         # extra SKILL.md section and asset files
            extra = os.path.join(REPO, skill["extra"])
            with open(os.path.join(extra, "extra.md"), encoding="utf-8") as fh:
                md = md.rstrip("\n") + "\n" + fh.read()
            for sub in sorted(os.listdir(extra)):
                if os.path.isdir(os.path.join(extra, sub)):
                    shutil.copytree(os.path.join(extra, sub), os.path.join(skill_dir, "assets", sub), dirs_exist_ok=True)
        if skill.get("router") and catalog["files"]:
            md = write_catalog(skill_dir, catalog, config, md)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
    if args.check:
        print(f"{changed} text(s) need a rebuild" if changed else "all bundled texts match the catalog")
        return 1 if changed else 0
    if args.render_only:
        return 0
    if args.shard:
        return 0
    autos = [sk for sk in config["skills"] if sk.get("auto") and (not args.only or sk["name"] in args.only)]
    if autos and not args.render_only:
        for sk in autos:                       # left out after review (crosscheck of the figures)
            excluded += sk.get("excluded_by_review", [])
        with open(os.path.join(REPO, "data", "corpus-excluded.json"), "w", encoding="utf-8") as fh:
            json.dump(excluded, fh, ensure_ascii=False, indent=1)
    path = os.path.join(REPO, "data", "build-report.json")
    prev = load_json(path) if os.path.exists(path) and args.only else []
    keep = [r for r in prev if r["skill"] not in {x["skill"] for x in report}]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(keep + report, fh, ensure_ascii=False, indent=1)
    return 1 if any("error" in r for r in report) else 0


if __name__ == "__main__":
    sys.exit(main())
