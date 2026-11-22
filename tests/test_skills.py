"""Checks on the built skills: structure, metadata and the lookup tools."""
import glob
import json
import os
import re
import subprocess
import sys
import unittest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SKILLS = sorted(glob.glob(os.path.join(REPO, "skills", "*")))
CONFIG = json.load(open(os.path.join(REPO, "countries", "ma", "skills.json"), encoding="utf-8"))


def run(skill, script, *args):
    return subprocess.run([sys.executable, os.path.join(REPO, "skills", skill, "scripts", script), *args],
                          capture_output=True, text=True, encoding="utf-8")


class Structure(unittest.TestCase):
    def test_every_configured_skill_is_built(self):
        self.assertEqual(sorted(os.path.basename(s) for s in SKILLS), sorted(s["name"] for s in CONFIG["skills"]))

    def test_skill_md_frontmatter(self):
        for s in SKILLS:
            md = open(os.path.join(s, "SKILL.md"), encoding="utf-8").read()
            m = re.match(r"^---\n(.*?)\n---\n", md, re.S)
            self.assertIsNotNone(m, s)
            self.assertIn(f"name: {os.path.basename(s)}\n", m.group(1) + "\n")
            self.assertIn("description:", m.group(1))
            self.assertNotIn("{{", md, f"unrendered placeholder in {s}")
            self.assertLess(len(md.splitlines()), 200)

    def test_every_text_has_files_and_provenance(self):
        ex_path = os.path.join(REPO, "data", "corpus-excluded.json")
        excluded = {e["slug"] for e in json.load(open(ex_path, encoding="utf-8"))} if os.path.exists(ex_path) else set()
        for sk in CONFIG["skills"]:
            for t in sk["texts"]:
                if sk.get("auto") and t["slug"] in excluded:
                    continue                      # left out by the quality gate, with its reason
                ref = os.path.join(REPO, "skills", sk["name"], "references", t["slug"])
                for f in ("text.md", "toc.md", "meta.json"):
                    self.assertTrue(os.path.isfile(os.path.join(ref, f)), f"{ref}/{f}")
                meta = json.load(open(os.path.join(ref, "meta.json"), encoding="utf-8"))
                self.assertEqual(meta["source_id"], t["id"])
                self.assertTrue(meta["source_url"].startswith("https://adala.justice.gov.ma/api/uploads/"))
                self.assertRegex(meta["pdf_sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(meta["n_articles"], 0, t["slug"])

    def test_no_mirrored_lam_alef_or_private_use_glyphs(self):
        # "خالل"/"أعاله"/"اإل" are what a broken extraction of خلال / أعلاه / الإ looks like
        for path in glob.glob(os.path.join(REPO, "skills", "*", "references", "*", "text.md")):
            text = open(path, encoding="utf-8").read()
            for bad in ("خالل", "أعاله", "اإل", "األ", "اآل"):
                self.assertNotIn(bad, text, f"{bad} in {path}")
            self.assertIsNone(re.search(r"[-�]", text), path)

    def test_article_numbers_are_unique_enough(self):
        for path in glob.glob(os.path.join(REPO, "skills", "*", "references", "*", "text.md")):
            nums = re.findall(r"^## (?:المادة|الفصل) (.+?)(?::.*)?$", open(path, encoding="utf-8").read(), re.M)
            dup = len(nums) - len(set(nums))
            self.assertLessEqual(dup, max(2, len(nums) // 100), f"{dup} duplicate headings in {path}")


class KnownFacts(unittest.TestCase):
    """Article counts that are public knowledge about these codes."""

    def meta(self, skill, slug):
        return json.load(open(os.path.join(REPO, "skills", skill, "references", slug, "meta.json"), encoding="utf-8"))

    def test_counts(self):
        self.assertEqual(self.meta("maroc-travail", "mudawwanat-shughl")["n_articles"], 589)
        self.assertEqual(self.meta("maroc-famille", "mudawwanat-usra")["n_articles"], 400)
        self.assertEqual(self.meta("maroc-immobilier", "huquq-ayniya-39-08")["n_articles"], 334)
        self.assertEqual(self.meta("maroc-droit", "dustur-2011")["n_articles"], 180)


class LawTool(unittest.TestCase):
    def test_list(self):
        r = run("maroc-travail", "law.py", "list")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("mudawwanat-shughl", r.stdout)

    def test_article_and_footer(self):
        r = run("maroc-travail", "law.py", "article", "mudawwanat", "43")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("## المادة 43", r.stdout)
        self.assertIn("أجل الإخطار", r.stdout)
        self.assertIn("https://adala.justice.gov.ma/", r.stdout)
        self.assertNotIn("## المادة 44", r.stdout)

    def test_word_order_inside_a_line(self):
        # this sentence came out with its words reversed when runs were taken in stream order
        r = run("maroc-travail", "law.py", "article", "mudawwanat", "1")
        self.assertIn("وخاصة المقاولات الصناعية والتجارية، ومقاولات الصناعة التقليدية", r.stdout)

    def test_range(self):
        r = run("maroc-travail", "law.py", "article", "mudawwanat", "43..45")
        self.assertEqual(len(re.findall(r"^## المادة", r.stdout, re.M)), 3)

    def test_sub_article(self):
        r = run("maroc-civil", "law.py", "article", "doc", "65-2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("## الفصل 65-2", r.stdout)

    def test_missing_article_fails_loudly(self):
        r = run("maroc-travail", "law.py", "article", "mudawwanat", "9999")
        self.assertEqual(r.returncode, 3)
        self.assertIn("NOT FOUND", r.stderr)

    def test_search_is_hamza_insensitive(self):
        a = run("maroc-travail", "law.py", "search", "الإخطار", "--text", "mudawwanat")
        b = run("maroc-travail", "law.py", "search", "الاخطار", "--text", "mudawwanat")
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(a.stdout, b.stdout)

    def test_search_no_hit(self):
        r = run("maroc-travail", "law.py", "search", "زرافةفضائية")
        self.assertEqual(r.returncode, 3)


class CatalogTool(unittest.TestCase):
    def test_stats_and_search(self):
        r = run("maroc-droit", "catalog.py", "stats")
        self.assertGreater(json.loads(r.stdout)["n_texts"], 4000)
        r = run("maroc-droit", "catalog.py", "search", "مدونة", "الشغل", "--lang", "ar")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"(?m)^428\tar\t")

    def test_law_number_spelling(self):
        a = run("maroc-droit", "catalog.py", "search", "65.99", "--max", "200")
        b = run("maroc-droit", "catalog.py", "search", "65-99", "--max", "200")
        self.assertEqual(a.stdout, b.stdout)

    def test_unknown_id(self):
        self.assertEqual(run("maroc-droit", "catalog.py", "show", "0").returncode, 3)


if __name__ == "__main__":
    unittest.main()
