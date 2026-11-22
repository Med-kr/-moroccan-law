"""Regression tests for defects found by the cross-checks (see scripts/crosscheck.py)."""
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import lawparse  # noqa: E402

try:
    import pdf_text  # needs pymupdf
    import build
except ImportError:  # pragma: no cover
    pdf_text = build = None


def L(*texts):
    return [{"t": t, "p": 1, "h": 16, "x0": 0, "x1": 0} for t in texts]


class Structure(unittest.TestCase):
    def parse(self, *lines, notes=None):
        return lawparse.parse(L(*lines), notes or {})

    def test_division_rank_follows_the_text(self):
        # customs code: الباب contains القسم (the code of obligations has it the other way round)
        r = self.parse("الباب الأول: البضائع", "القسم الأول: التعريف", "الفصل 1", "نص.", "القسم الثاني: الآثار",
                       "الفصل 2", "نص.", "الباب الثاني: المنازعات", "الفصل 3", "نص.")
        arts = [a for a in r["parts"][0] if not a.get("block")]
        self.assertEqual(arts[0]["path"], ["الباب الأول: البضائع", "القسم الأول: التعريف"])
        self.assertEqual(arts[1]["path"], ["الباب الأول: البضائع", "القسم الثاني: الآثار"])
        self.assertEqual(arts[2]["path"], ["الباب الثاني: المنازعات"])

    def test_sub_section_does_not_replace_its_section(self):
        r = self.parse("القسم الأول: النظام", "الباب الأول: الخدمات", "القسم الفرعي الأول: التوقيع", "المادة 1", "نص.")
        self.assertEqual(r["parts"][0][0]["path"],
                         ["القسم الأول: النظام", "الباب الأول: الخدمات", "القسم الفرعي الأول: التوقيع"])

    def test_text_under_a_title_is_not_taken_for_its_second_line(self):
        lines = L("المادة 1", "نص.", "الباب الثاني", "أحكام زجرية", "نص قصير يتبع العنوان", "المادة 2", "نص.")
        for l, (x0, x1) in zip(lines, [(250, 350), (100, 500), (240, 360), (230, 370), (100, 480), (250, 350), (100, 500)]):
            l["x0"], l["x1"] = x0, x1
        lines += [{"t": "سطر كامل من النص.", "p": 1, "h": 16, "x0": 100, "x1": 500} for _ in range(40)]
        r = lawparse.parse(lines, {})
        whole = " ".join(a["text"] for a in r["parts"][0])
        self.assertIn("نص قصير يتبع العنوان", whole)                       # full-width line: text
        self.assertEqual(r["parts"][0][-1]["path"], ["الباب الثاني أحكام زجرية"])  # centred line: title

    def test_cross_reference_wrapped_just_before_the_real_heading(self):
        r = self.parse("الفصل 11: شروط التجنيس", "مع مراعاة الأحوال المنصوص عليها في", "الفصل 12:", "أولا - الإقامة.",
                       "الفصل 12: استثناءات", "يجوز تجنيس الأجنبي.", "الفصل 13", "نص.")
        arts = r["parts"][0]
        self.assertEqual([a["num"] for a in arts], ["11", "12", "13"])
        self.assertIn("أولا - الإقامة", arts[0]["text"])
        self.assertEqual(arts[1]["heading"], "الفصل 12: استثناءات")

    def test_articles_quoted_by_an_amending_law_are_not_its_own(self):
        r = self.parse("المادة الأولى", "تتمم أحكام القانون بالمواد التالية:", "المادة 647-1. - تختص الإدارة.",
                       "المادة 647-2. - تقوم النيابة العامة.", "المادة 647-3. - يستفيد المحكوم عليه.",
                       "المادة الثانية", "يدخل هذا القانون حيز التنفيذ.")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["1", "2"])
        self.assertIn("647-2", r["parts"][0][0]["text"])

    def test_inserted_articles_of_a_code_are_articles(self):
        r = self.parse("الفصل 34", "نص.", "الفصل 35", "نص.", "الفصل 35-1. - العقوبات البديلة هي.", "الفصل 35-2. - تحدد.",
                       "الفصل 36", "نص.")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["34", "35", "35-1", "35-2", "36"])

    def test_en_dash_and_glued_footnote_mark(self):
        r = lawparse.parse(L("Article 230", "Texte.", "Article 231", "Texte.", "Article 231–1", "Texte.", "Article 232",
                             "Texte du présent article.") + L(*["Texte de l'article en français."] * 5), {})
        self.assertEqual([a["num"] for a in r["parts"][0]], ["230", "231", "231-1", "232"])
        r = lawparse.parse(L("Article 501", "Texte.", "Article 502", "Texte.", "Article 50370", "Texte.", "Article 504",
                             "Texte.", "Article 505", "Texte.") + L(*["Texte de l'article en français."] * 5), {"70": "note"})
        self.assertEqual([a["num"] for a in r["parts"][0]], ["501", "502", "503", "504", "505"])
        self.assertEqual(r["parts"][0][2]["notes"], {"70": "note"})


class Footnotes(unittest.TestCase):
    def parse(self, *lines, notes=None):
        return lawparse.parse(L(*lines), notes or {})

    def test_no_footnote_is_lost(self):
        notes = {"1": "الجريدة الرسمية", "2": "عنوان الباب", "3": "نص", "4": "بلا إحالة"}
        r = self.parse("قانون تجريبي[^1]", "الباب الأول[^2]", "المادة 1", "نص[^3].", "المادة 2", "نص.", notes=notes)
        self.assertEqual(r["header_notes"], {"1": "الجريدة الرسمية"})
        self.assertEqual(r["parts"][0][0]["notes"], {"2": "عنوان الباب", "3": "نص"})
        self.assertEqual(r["orphan_notes"], {"4": "بلا إحالة"})


@unittest.skipIf(pdf_text is None, "pymupdf not installed")
class NoteZone(unittest.TestCase):
    def page(self, *rows):
        return {"p": 1, "lines": [{"t": t, "h": h, "y": 800 - 20 * i, "x0": 70, "x1": 520, **extra}
                                   for i, (t, h, extra) in enumerate(rows)]}

    def split(self, *pages):
        filler = self.page(*[("نص من متن القانون في سطر كامل.", 16, {})] * 30)
        return pdf_text.split_body_footnotes([filler, *pages])

    def test_dash_number_inside_a_note_is_not_a_new_note(self):
        body, notes, _ = self.split(self.page(
            ("نص المادة[^1].", 16, {}),
            ("1 - انظر المادة 19:", 13, {}),
            ("- 24 ساعة لتسليم الوصل؛", 13, {}),
            ("2 - انظر المادة 25.", 13, {})))
        self.assertEqual(sorted(notes), ["1", "2"])
        self.assertIn("24 ساعة", notes["1"])

    def test_number_skipped_by_the_source(self):
        body, notes, stats = self.split(self.page(
            ("نص.", 16, {}), ("1 - أ.", 13, {}), ("2 - ب.", 13, {}), ("5 - ج.", 13, {}), ("6 - د.", 13, {})))
        self.assertEqual(sorted(notes, key=int), ["1", "2", "5", "6"])
        self.assertEqual(stats["footnote_numbers_missing"], [3, 4])

    def test_raised_number_and_shared_note(self):
        body, notes, _ = self.split(self.page(
            ("نص.", 16, {}), ("غير وتمم بالمادة الثانية.", 13, {"mark": [1]}), ("22 من ربيع الأول 1414.", 13, {}),
            ("غير وتمم بالفصل الأول.", 13, {"mark": [2, 3]})))
        self.assertEqual(notes["1"], "غير وتمم بالمادة الثانية.\n22 من ربيع الأول 1414.")
        self.assertEqual(notes["2"], notes["3"])

    def test_notes_only_one_point_smaller_and_note_printed_at_body_size(self):
        body, notes, _ = self.split(self.page(
            ("نص.", 16, {}), ("1 - انظر المادة 3.", 13, {}), ("2 - تم نسخ المادتين 4 و5", 16, {}), ("بمقتضى القانون.", 16, {}),
            ("- 2 -", 16, {})))
        self.assertEqual(sorted(notes), ["1", "2"])
        self.assertEqual(notes["2"], "تم نسخ المادتين 4 و5\nبمقتضى القانون.")
        self.assertNotIn("بمقتضى القانون.", [b["t"] for b in body])

    def test_page_number_drawn_right_to_left(self):
        self.assertTrue(pdf_text.PAGE_NO.match("4 --"))
        self.assertTrue(pdf_text.PAGE_NO.match("- 4 -"))


@unittest.skipIf(build is None, "pymupdf not installed")
class SourceNumbers(unittest.TestCase):
    def test_reversed_dahir_number(self):
        fix = lambda t: build.DAHIR_REVERSED.sub(r"\1\4.\2.\3", t)
        self.assertEqual(fix("ظهير شريف رقم 11.03.1 بتاريخ"), "ظهير شريف رقم 1.11.03 بتاريخ")
        self.assertEqual(fix("الظهير الشريف بمثابة قانون رقم 74.447.1 بتاريخ"), "الظهير الشريف بمثابة قانون رقم 1.74.447 بتاريخ")
        self.assertEqual(fix("المرسوم رقم 09.165.2،"), "المرسوم رقم 2.09.165،")
        self.assertEqual(fix("الظهير الشريف رقم 1.11.03 بتاريخ"), "الظهير الشريف رقم 1.11.03 بتاريخ")
        self.assertEqual(fix("القانون رقم 31.08.1"), "القانون رقم 31.08.1")

    def test_glyph_table_only_corrects_towards_arabic(self):
        table = pdf_text.glyph_table()
        self.assertTrue(table, "data/glyph-table.json is missing: run scripts/glyph_table.py")
        for font, glyphs in table.items():
            for g, u in glyphs.items():
                self.assertTrue(pdf_text._has_arabic(u), (font, g, u))


if __name__ == "__main__":
    unittest.main()
