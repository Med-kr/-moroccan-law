import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import lawparse  # noqa: E402


def L(*texts):
    return [{"t": t, "p": 1, "h": 16, "x0": 0, "x1": 0} for t in texts]


class Ordinals(unittest.TestCase):
    def test_values(self):
        cases = {"الأولى": 1, "الأول": 1, "الثانية": 2, "العاشر": 10, "الحادي عشر": 11, "الثانية عشرة": 12,
                 "العشرون": 20, "الحادية والعشرون": 21, "السادس والثلاثون": 36, "الفريدة": 1}
        for text, value in cases.items():
            self.assertEqual(lawparse.ordinal_value(text), value, text)

    def test_not_an_ordinal(self):
        self.assertIsNone(lawparse.ordinal_value("المذكور"))


class Headings(unittest.TestCase):
    def parse(self, *lines, notes=None):
        return lawparse.parse(L(*lines), notes or {})

    def test_simple_sequence(self):
        r = self.parse("قانون تجريبي", "المادة 1", "نص أول.", "المادة 2", "نص ثان.", "المادة 3", "نص ثالث.")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["1", "2", "3"])
        self.assertEqual(r["header"], ["قانون تجريبي"])
        self.assertEqual(r["anomalies"], [])

    def test_wrapped_cross_reference_is_not_a_heading(self):
        r = self.parse("المادة 1", "نص.", "المادة 2", "طبقا لما هو منصوص عليه في", "المادة 30", "أعلاه.",
                       "المادة 3", "نص.", "المادة 4", "نص.")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["1", "2", "3", "4"])
        self.assertIn("المادة 30", r["parts"][0][1]["text"])
        self.assertTrue(any("kept as text" in a for a in r["anomalies"]))

    def test_repealed_range_is_accepted_and_reported(self):
        lines = []
        for n in list(range(1, 4)) + list(range(40, 44)):
            lines += [f"الفصل {n}", "نص."]
        r = self.parse(*lines)
        self.assertEqual(r["n_articles"], 7)
        self.assertTrue(any("numbering gap: 3 -> 40" in a for a in r["anomalies"]))

    def test_sub_articles_and_bis(self):
        r = self.parse("الفصل 64", "نص.", "الفصل 65", "نص.", "الفصل 1-65", "نص.", "الفصل 2-65", "نص.",
                       "الفصل 65 مكرر", "نص.", "الفصل 66", "نص.")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["64", "65", "65-1", "65-2", "65 مكرر", "66"])

    def test_ordinal_headings_with_titles(self):
        r = self.parse("الفصل الأول: تعريف", "نص.", "الفصل الثاني: مجال التطبيق", "نص.", "الفصل الثالث", "نص.")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["1", "2", "3"])
        self.assertEqual(r["parts"][0][1]["heading"], "الفصل 2: مجال التطبيق")

    def test_keyword_choice_and_structure_path(self):
        r = self.parse("الباب الأول: أحكام عامة", "الفصل الأول: تعاريف", "المادة 1", "نص.", "المادة 2", "نص.",
                       "الفصل الثاني: التطبيق", "المادة 3", "نص.")
        self.assertEqual(r["article_keyword"], "المادة")
        self.assertEqual(r["parts"][0][2]["path"], ["الباب الأول: أحكام عامة", "الفصل الثاني: التطبيق"])

    def test_numbering_restart_makes_a_new_part(self):
        r = self.parse("المادة 1", "ينفذ القانون.", "المادة 2", "ينشر.", "المادة 1", "نص.", "المادة 2", "نص.",
                       "المادة 3", "نص.")
        self.assertEqual([len(p) for p in r["parts"]], [2, 3])
        self.assertEqual(r["main_part"], 1)

    def test_footnotes_attach_to_their_article(self):
        r = self.parse("المادة 1", "نص[^7].", "المادة 2[^8]", "نص.", notes={"7": "هامش سبعة", "8": "هامش ثمانية"})
        self.assertEqual(r["parts"][0][0]["notes"], {"7": "هامش سبعة"})
        self.assertEqual(r["parts"][0][1]["notes"], {"8": "هامش ثمانية"})

    def test_paragraph_reflow(self):
        text = lawparse.join_paragraphs(["يكون إنهاء عقد الشغل مبنيا على", "احترام أجل الإخطار.", "- حالة أولى؛", "- حالة ثانية."])
        self.assertEqual(text.split("\n\n"), ["يكون إنهاء عقد الشغل مبنيا على احترام أجل الإخطار.", "- حالة أولى؛", "- حالة ثانية."])

    def test_consolidation_date(self):
        self.assertEqual(lawparse.consolidation_date(L("مدونة الشغل", "صيغة محينة بتاريخ 16 يوليو 2026")), "16 يوليو 2026")


if __name__ == "__main__":
    unittest.main()


class NewForms(unittest.TestCase):
    def parse(self, *lines):
        return lawparse.parse(L(*lines), {})

    def test_dotted_sub_articles_written_sub_first(self):
        # right-to-left layout prints 4.1 as "1.4"
        r = self.parse("المادة 3", "نص.", "المادة 4", "نص.", "المادة 1.4", "نص.", "المادة 2.4", "نص.",
                       "المادة 5.4", "نص.", "المادة 5", "نص.")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["3", "4", "4.1", "4.2", "4.5", "5"])
        self.assertEqual(r["anomalies"], ["numbering gap: 0 -> 3 (page 1); usually a repealed range, check the footnote"])

    def test_heading_with_text_on_the_same_line(self):
        r = self.parse("المادة الأولى. - يراد بما يلي نص أول.", "المادة الأولى مكررة. - نص مكرر.",
                       "المادة الثانية. - نص ثان.", "المادة الثالثة. - نص ثالث.")
        arts = r["parts"][0]
        self.assertEqual([a["num"] for a in arts], ["1", "1 مكرر", "2", "3"])
        self.assertEqual(arts[0]["text"], "يراد بما يلي نص أول.")

    def test_ordinal_without_hamza(self):
        r = self.parse("الفصل الاول", "نص.", "الفصل 2", "نص.", "الفصل 3", "نص.")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["1", "2", "3"])


class French(unittest.TestCase):
    def test_french_text(self):
        r = lawparse.parse(L("Code de la famille", "Version consolidée en date du 4 février 2016",
                             "LIVRE PREMIER: DU MARIAGE", "Chapitre premier: Dispositions générales",
                             "Article premier", "La présente loi est dénommée Code de la Famille.",
                             "Article 2", "Les dispositions du présent Code s'appliquent :", "1) à tous les Marocains ;",
                             "Article 2-1", "Texte ajouté, conformément à",
                             "l'article 40 ci-dessus.", "Article 3", "Le ministère public est partie principale."), {})
        self.assertEqual(r["lang"], "fr")
        self.assertEqual(r["article_keyword"], "Article")
        self.assertEqual([a["num"] for a in r["parts"][0]], ["1", "2", "2-1", "3"])
        self.assertEqual(r["consolidated_on"], "4 février 2016")
        self.assertEqual(r["parts"][0][0]["path"], ["LIVRE PREMIER: DU MARIAGE", "Chapitre premier: Dispositions générales"])
        self.assertIn("l'article 40 ci-dessus.", r["parts"][0][2]["text"])

    def test_arabic_stays_arabic(self):
        r = lawparse.parse(L("المادة 1", "نص يذكر Article 5 بالفرنسية.", "المادة 2", "نص."), {})
        self.assertEqual(r["lang"], "ar")
