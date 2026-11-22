"""Fixes from the legal audit: article-number matching, repeal notes, transitional provisions,
religious-holiday warning, footnotes set in the body font, keyword-less division titles,
documented source errata, freshness of amendments."""
import datetime as dt
import json
import os
import subprocess
import sys
import unittest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import delais  # noqa: E402
import law  # noqa: E402
import lawparse  # noqa: E402


def skill(name, script, *args):
    p = subprocess.run([sys.executable, os.path.join(REPO, "skills", name, "scripts", script), *args],
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class ArticleNumbers(unittest.TestCase):
    def test_canonical_forms(self):
        for a, b in [("353 bis", "353 المكررة"), ("353bis", "353 مكرر"), ("65-1", "65.1"),
                     ("65 - 1", "65-1"), ("1er", "1"), ("Premier", "1"), ("12 ter", "12 مكرر مرتين")]:
            self.assertEqual(law.canon(a), law.canon(b), (a, b))
        self.assertNotEqual(law.canon("353"), law.canon("353 bis"))

    def test_bis_lookup_in_french_and_arabic(self):
        code, out, err = skill("maroc-commerce", "law.py", "article", "sharikat-musahama-fr", "353", "353 bis")
        self.assertEqual(code, 0, err)
        self.assertIn("## Article 353\n", out)
        self.assertIn("## Article 353 bis", out)
        code, out, err = skill("maroc-commerce", "law.py", "article", "sharikat-musahama-17-95", "353 bis")
        self.assertEqual(code, 0, err)


class SourceErrata(unittest.TestCase):
    def test_swapped_labels_corrected_and_documented(self):
        # official French PDF prints the text of 353 under "353 bis" and the reverse
        code, out, _ = skill("maroc-commerce", "law.py", "article", "sharikat-musahama-fr", "353", "353 bis")
        a353 = out.split("## Article 353 bis")[0]
        self.assertIn("action sociale", a353)
        self.assertIn("restituer", out.split("## Article 353 bis")[1])
        meta = json.load(open(os.path.join(REPO, "skills", "maroc-commerce", "references",
                                           "sharikat-musahama-fr", "meta.json"), encoding="utf-8"))
        self.assertEqual(len(meta["source_corrections"]), 2)
        self.assertTrue(all(c["why"] for c in meta["source_corrections"]))

    def test_letter_l_for_digit_one(self):
        self.assertEqual(lawparse.match_heading_fr("Article 3l")[0], "31")
        self.assertIsNone(lawparse.match_heading_fr("Article Il est"))

    def test_heading_runon_with_footnote_mark(self):
        num, refs, _, rest = lawparse.match_heading_fr("Article 353[^119] Lorsque des profits")
        self.assertEqual((num, refs), ("353", "[^119]"))
        self.assertTrue(rest.startswith("Lorsque"))
        self.assertIsNone(lawparse.match_heading_fr("Article 352 ci-dessus est applicable"))


class RepealNotes(unittest.TestCase):
    def test_repealed_range_explained(self):
        code, out, err = skill("maroc-civil", "law.py", "article", "doc", "330")
        self.assertEqual(code, 3)
        self.assertIn("NOT FOUND", err)
        self.assertIn("325", out)
        self.assertIn("334", out)

    def test_criminal_code_footnote_in_body_font(self):
        code, out, _ = skill("maroc-penal", "law.py", "article", "qanun-jinai", "493")
        self.assertIn("[^173]: ", out)
        self.assertNotIn("\n173 - ", out)


class Transitional(unittest.TestCase):
    def test_civil_procedure_application_in_time(self):
        code, out, err = skill("maroc-procedure-civile", "law.py", "transitional", "msm-58-25")
        self.assertEqual(code, 0, err)
        for n in ("641", "643", "644"):
            self.assertIn(f"## المادة {n}", out)
        self.assertIn("بالآجال", out)
        self.assertIn("مقتضيات انتقالية وختامية", out)   # the keyword-less title is a division now

    def test_unnamed_division_title(self):
        body = [{"t": "المادة 1", "p": 1, "h": 10}, {"t": "نص المادة الأولى.", "p": 1, "h": 10},
                {"t": "مقتضيات انتقالية وختامية", "p": 1, "h": 10},
                {"t": "المادة 2", "p": 1, "h": 10}, {"t": "يدخل هذا القانون حيز التنفيذ.", "p": 1, "h": 10}]
        r = lawparse.parse(body, {})
        arts = r["parts"][r["main_part"]]
        self.assertNotIn("مقتضيات", arts[0]["text"])
        self.assertEqual(arts[1]["path"], ["مقتضيات انتقالية وختامية"])


class ReligiousHolidays(unittest.TestCase):
    def test_tabular_calendar_matches_announced_dates(self):
        # dates announced in Morocco
        self.assertEqual(delais.hijri_to_date(1446, 10, 1), dt.date(2025, 3, 31))   # عيد الفطر
        self.assertEqual(delais.hijri_to_date(1446, 12, 10), dt.date(2025, 6, 7))   # عيد الأضحى
        self.assertEqual(delais.hijri_to_date(1447, 1, 1), dt.date(2025, 6, 27))    # فاتح محرم

    def test_warning_without_extension(self):
        code, out, err = skill("maroc-procedure-civile", "delais.py", "calc", "--from", "2027-02-07", "--days", "30")
        self.assertEqual(code, 0, err)
        self.assertIn("عيد الفطر", out)
        self.assertIn("لم يمدد الأجل آليا", out)
        self.assertIn("الأربعاء 10 مارس 2027", out)


class TimeLimitRules(unittest.TestCase):
    def test_restart_after_change_of_capacity(self):
        # art. 212: runs anew 15 days after the new notification (2 Nov -> 17 Nov), then 30 full days
        code, out, err = skill("maroc-procedure-civile", "delais.py", "calc", "--from", "2026-10-01", "--days", "30",
                               "--restart", "212:2026-11-02")
        self.assertEqual(code, 0, err)
        self.assertIn("الجمعة 18 دجنبر 2026", out.split("==>")[1])

    def test_platform_down_on_last_day(self):
        code, out, err = skill("maroc-procedure-civile", "delais.py", "calc", "--from", "2026-11-03", "--days", "30",
                               "--electronic", "--platform-back", "2026-12-07")
        self.assertEqual(code, 0, err)
        self.assertIn("المادة 639", out)
        self.assertIn("الثلاثاء 8 دجنبر 2026", out.split("==>")[1])


class RunOnHeadings(unittest.TestCase):
    def test_marks_in_front_of_numbers_and_quoted_heading(self):
        for sk, text, num, words in [("maroc-administratif", "maa-36-15", "31", "يمنح الترخيص"),
                                     ("maroc-assurances-banques", "sayr-52-05", "61-1", "صفائح التسجيل"),
                                     ("maroc-immobilier", "taamir-12-90", "70", "تطبق مقتضيات"),
                                     ("maroc-commerce", "taawuniyat-112-12", "68", "السنة المحاسبية")]:
            code, out, err = skill(sk, "law.py", "article", text, num)
            self.assertEqual(code, 0, (text, num, err))
            self.assertIn(words, out)


class Corpus(unittest.TestCase):
    def test_find_by_number_and_read(self):
        code, out, err = skill("maroc-corpus", "law.py", "find", "59.21")
        self.assertEqual(code, 0, err)
        rows = out.strip().splitlines()
        self.assertEqual(len(rows), 1, rows)                     # exact number, not 21.24
        self.assertIn("بالتعليم المدرسي", rows[0])
        code, out, err = skill("maroc-corpus", "law.py", "article", rows[0].split("\t")[0], "1")
        self.assertEqual(code, 0, err)
        self.assertIn("51.17", out)

    def test_quality_gate_left_out_garbled_texts(self):
        ex = json.load(open(os.path.join(REPO, "data", "corpus-excluded.json"), encoding="utf-8"))
        reasons = " ".join(e["reason"] for e in ex)
        self.assertIn("impossible dates", reasons)
        built = set(os.listdir(os.path.join(REPO, "skills", "maroc-corpus", "references")))
        self.assertFalse(built & {e["slug"] for e in ex})
        import build
        for slug in list(built)[:400]:
            text = open(os.path.join(REPO, "skills", "maroc-corpus", "references", slug, "text.md"), encoding="utf-8").read()
            self.assertLess(len(build.impossible_dates(text)), 3, slug)

    def test_corpus_skill_is_short(self):
        md = open(os.path.join(REPO, "skills", "maroc-corpus", "SKILL.md"), encoding="utf-8").read()
        self.assertLess(len(md), 8000)                            # no table of 700 texts in Claude's context
        self.assertIn("pas été relus un par un", md)


class Freshness(unittest.TestCase):
    def test_every_known_amending_law_is_cited(self):
        p = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "freshness.py")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


class Review(unittest.TestCase):
    def test_every_parser_note_is_reviewed(self):
        p = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "review_anomalies.py")],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_legal_review_set(self):
        p = subprocess.run([sys.executable, os.path.join(REPO, "evals", "legal", "run.py")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout[-800:])          # every expected answer is in its article
        res = json.load(open(os.path.join(REPO, "evals", "legal", "results.json"), encoding="utf-8"))["summary"]
        self.assertGreaterEqual(res["retrieved_top"], 38)

    def test_holdout_set(self):
        # written after the search was tuned, never used to tune it
        p = subprocess.run([sys.executable, os.path.join(REPO, "evals", "legal", "run.py"), "--set", "holdout"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout[-800:])
        res = json.load(open(os.path.join(REPO, "evals", "legal", "results-holdout.json"), encoding="utf-8"))["summary"]
        self.assertGreaterEqual(res["retrieved_top"], 17)

    def test_divergence_between_versions_is_shown(self):
        code, out, _ = skill("maroc-travail", "law.py", "article", "mudawwanat-shughl", "256")
        self.assertIn("!! اختلاف بين النسختين", out)


class Search(unittest.TestCase):
    def test_prefixes_hamza_and_synonyms(self):
        for sk, text, words, art in [
                ("maroc-travail", "mudawwanat-shughl", ["فترة التجربة", "الأطر"], "14"),
                ("maroc-travail", "mudawwanat-shughl", ["الأخطاء الجسيمة"], "39"),
                ("maroc-civil", "doc", ["الشرط الجزائي"], "264"),
                ("maroc-civil", "doc", ["مسؤول عن الضرر", "بخطئه"], "78"),
                ("maroc-administratif", "taalil-03-01", ["تعليل قراراتها"], "1")]:
            code, out, err = skill(sk, "law.py", "search", *words, "--text", text, "--max", "3")
            self.assertEqual(code, 0, err)
            first = [l for l in out.splitlines() if l.startswith("- ")][:3]
            self.assertTrue(any(f" {art}:" in l or f" {art} (" in l for l in first), (words, first))

    def test_stem(self):
        self.assertEqual(law.stem("للأطر"), law.stem("الأطر"))
        self.assertEqual(law.stem("بخطإه"), law.stem("بخطئه"))
        self.assertEqual(law.stem("الآجال"), law.stem("آجال"))
        self.assertNotEqual(law.stem("كتابة"), law.stem("تابة"))


if __name__ == "__main__":
    unittest.main()
