"""Article cards (status, amending laws, Bulletin officiel), titled articles, AR/FR side by side."""
import json
import os
import subprocess
import sys
import unittest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def run(skill, *args):
    p = subprocess.run([sys.executable, os.path.join(REPO, "skills", skill, "scripts", "law.py"), *args],
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def card(skill, text, num):
    code, out, err = run(skill, "card", text, num, "--json")
    return json.loads(out) if out.strip() else {"error": err}


class Status(unittest.TestCase):
    def test_known_statuses(self):
        for skill, text, num, status in [
                ("maroc-civil", "doc", "726", "repealed"),                 # repealed by law 25.95
                ("maroc-civil", "doc", "330", "repealed"),                 # repealed range 325-334 (1939)
                ("maroc-civil", "doc", "264", "amended"),                  # paragraphs added by 27.95
                ("maroc-penal", "qanun-jinai", "448-1", "added"),          # section added by 27.14
                ("maroc-assurances-banques", "sayr-52-05", "61-1", "added"),
                ("maroc-assurances-banques", "sayr-52-05", "24", "replaced"),
                ("maroc-travail", "mudawwanat-shughl", "184", "as printed (no amendment noted)")]:
            c = card(skill, text, num)
            self.assertEqual(c.get("status"), status, (text, num, c))

    def test_bulletin_officiel_found_through_earlier_note(self):
        # the note under 24 says "السالف الذكر": the BO reference comes from the first note citing 116.14
        c = card("maroc-assurances-banques", "sayr-52-05", "24")
        am = c["amendments"][0]
        self.assertEqual(am["by"], "116.14")
        self.assertEqual(am["bulletin_officiel"]["issue"], "6490")

    def test_finance_law_named_as_amending_text(self):
        c = card("maroc-administratif", "mahakim-maliya-62-99", "55")
        self.assertIn("38.07", [a["by"] for a in c["amendments"]])

    def test_warning_and_counterpart(self):
        c = card("maroc-travail", "mudawwanat-shughl", "256")
        self.assertTrue(any("اختلاف" in w for w in c["warnings"]))
        self.assertEqual(c["counterpart"]["text"], "mudawwanat-shughl-fr")

    def test_internal_references(self):
        c = card("maroc-procedure-civile", "msm-58-25", "204")
        self.assertEqual(c["references"]["same_text"], ["83", "84", "86", "115"])


class Lookup(unittest.TestCase):
    def test_titled_articles_found_by_number(self):
        code, out, err = run("maroc-famille", "article", "jinsiya", "12")
        self.assertEqual(code, 0, err)
        self.assertIn("## الفصل 12: استثناءات", out)

    def test_both_versions_side_by_side(self):
        code, out, err = run("maroc-civil", "both", "doc", "230")
        self.assertEqual(code, 0, err)
        self.assertIn("تقوم مقام القانون", out)
        self.assertIn("tiennent lieu de loi", out)

    def test_source_typos_in_headings(self):
        code, out, err = run("maroc-civil", "article", "doc", "106-13")          # « المادة 13-106 » in the PDF
        self.assertEqual(code, 0, err)
        code, out, err = run("maroc-civil", "article", "doc-fr", "65-6")         # « Articles 65-6 » in the PDF
        self.assertEqual(code, 0, err)
        code, out, err = run("maroc-civil", "article", "doc-fr", "618-3 quater")  # « qua ter » in the PDF
        self.assertEqual(code, 0, err)


class Divergences(unittest.TestCase):
    def test_report(self):
        subprocess.run([sys.executable, os.path.join(REPO, "scripts", "divergences.py")], capture_output=True, check=True)
        d = {x["arabic"]: x for x in json.load(open(os.path.join(REPO, "data", "divergences-ar-fr.json"), encoding="utf-8"))}
        self.assertEqual(d["jinsiya"]["only_in_arabic"], [])               # titled articles compared by number
        self.assertIn("35-1", d["qanun-jinai"]["only_in_arabic"])          # alternative sanctions, 2024
        self.assertEqual(d["doc"]["only_in_arabic"], [])
        self.assertEqual(d["doc"]["only_in_french"], [])


class Mcp(unittest.TestCase):
    def test_article_card_tool(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "article_card", "arguments": {"text": "qanun-jinai", "number": "448-1"}}}
        p = subprocess.run([sys.executable, os.path.join(REPO, "mcp", "server.py")], input=json.dumps(msg) + "\n",
                           capture_output=True, text=True)
        c = json.loads(json.loads(p.stdout)["result"]["content"][0]["text"])
        self.assertEqual(c["status"], "added")


if __name__ == "__main__":
    unittest.main()
