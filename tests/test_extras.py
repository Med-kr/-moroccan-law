"""Tools added on top of the lookup: MCP server, comparison, time limits, French versions."""
import json
import os
import subprocess
import sys
import unittest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PROC = os.path.join(REPO, "skills", "maroc-procedure-civile", "scripts")


def run(script, *args, stdin=None):
    p = subprocess.run([sys.executable, script, *args], capture_output=True, text=True, input=stdin)
    return p.returncode, p.stdout, p.stderr


class Mcp(unittest.TestCase):
    def rpc(self, *msgs):
        code, out, err = run(os.path.join(REPO, "mcp", "server.py"), stdin="\n".join(json.dumps(m) for m in msgs) + "\n")
        self.assertEqual(code, 0, err)
        return [json.loads(l) for l in out.splitlines()]

    def test_handshake_and_tools(self):
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                     {"jsonrpc": "2.0", "method": "notifications/initialized"},
                     {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(len(r), 2)                      # the notification gets no answer
        self.assertEqual(r[0]["result"]["protocolVersion"], "2025-06-18")
        names = {t["name"] for t in r[1]["result"]["tools"]}
        self.assertLessEqual({"list_texts", "get_article", "search_articles", "catalog_search"}, names)

    def test_get_article_and_not_found(self):
        call = lambda i, n: {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                             "params": {"name": "get_article", "arguments": {"text": "mudawwanat-usra", "numbers": [n]}}}
        r = self.rpc(call(1, "19"), call(2, "99999"))
        self.assertIn("المادة 19", r[0]["result"]["content"][0]["text"])
        self.assertIn("adala.justice.gov.ma", r[0]["result"]["content"][0]["text"])
        self.assertIn("NOT FOUND", r[1]["result"]["content"][0]["text"])

    def test_unknown_tool_and_method(self):
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "nope"}},
                     {"jsonrpc": "2.0", "id": 2, "method": "nope"})
        self.assertEqual(r[0]["error"]["code"], -32602)
        self.assertEqual(r[1]["error"]["code"], -32601)

    def test_self_test(self):
        code, out, _ = run(os.path.join(REPO, "mcp", "server.py"), "--self-test")
        self.assertEqual(code, 0, out)


class TimeLimits(unittest.TestCase):
    def calc(self, *args):
        code, out, err = run(os.path.join(PROC, "delais.py"), "calc", *args)
        self.assertEqual(code, 0, err)
        return out

    def test_full_time_limit(self):
        # notified Tuesday 3 Nov 2026, 30 days: last day of the period 3 Dec, act possible on Friday 4 Dec
        out = self.calc("--from", "2026-11-03", "--days", "30")
        self.assertIn("==> آخر يوم يمكن فيه القيام بالإجراء: الجمعة 4 دجنبر 2026", out)
        self.assertIn("المادة 602", out)

    def test_weekend_and_fixed_holiday_extend(self):
        # 2 Oct 2026 + 30 days -> Sunday 1 Nov; next day Monday 2 Nov is a working day
        self.assertIn("==> آخر يوم يمكن فيه القيام بالإجراء: الاثنين 2 نونبر 2026", self.calc("--from", "2026-10-02", "--days", "30"))
        # 3 Nov + 14 days -> 17 Nov, +1 = Wednesday 18 Nov (Independence Day) -> Thursday 19 Nov
        out = self.calc("--from", "2026-11-03", "--days", "14")
        self.assertIn("عيد الاستقلال", out)
        self.assertIn("==> آخر يوم يمكن فيه القيام بالإجراء: الخميس 19 نونبر 2026", out)

    def test_extra_holidays_months_and_electronic(self):
        out = self.calc("--from", "2026-11-03", "--days", "30", "--holidays", "2026-12-04")
        self.assertIn("==> آخر يوم يمكن فيه القيام بالإجراء: الاثنين 7 دجنبر 2026", out)
        self.assertIn("الأربعاء 31 مارس 2027", self.calc("--from", "2027-01-31", "--months", "2", "--electronic"))
        self.assertIn("28 فبراير 2027", self.calc("--from", "2027-01-31", "--months", "1", "--electronic"))

    def test_fixed_holidays_come_from_the_decree(self):
        sys.path.insert(0, PROC)
        import delais
        text = open(os.path.join(PROC, "..", "references", "ayam-al-ayad-2-77-169", "text.md"), encoding="utf-8").read()
        for name in delais.FIXED.values():
            self.assertIn(name, text, name)
        self.assertEqual(len(delais.FIXED), 11)

    def test_list_finds_the_appeal_period(self):
        code, out, _ = run(os.path.join(PROC, "delais.py"), "list", "الاستئناف", "--text", "msm-58-25", "--max", "200")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"المادة 204: .*ثلاثين \(30\) يوما")


class Compare(unittest.TestCase):
    def test_new_appeal_article_matches_the_old_one(self):
        code, out, err = run(os.path.join(PROC, "compare.py"), "msm-58-25", "204", "--in", "msm-1974", "--top", "1")
        self.assertEqual(code, 0, err)
        self.assertIn("## الفصل 134", out)
        self.assertIn("ليس جدول مقابلة رسميا", out)

    def test_unknown_article(self):
        code, _, err = run(os.path.join(PROC, "compare.py"), "msm-58-25", "99999")
        self.assertEqual(code, 3)
        self.assertIn("NOT FOUND", err)


class FrenchVersions(unittest.TestCase):
    def law(self, skill, *args):
        return run(os.path.join(REPO, "skills", skill, "scripts", "law.py"), *args)

    def test_same_article_count_as_arabic(self):
        for skill, ar, fr in (("maroc-famille", "mudawwanat-usra", "mudawwanat-usra-fr"),
                              ("maroc-travail", "mudawwanat-shughl", "mudawwanat-shughl-fr"),
                              ("maroc-immobilier", "huquq-ayniya-39-08", "huquq-ayniya-fr"),
                              ("maroc-droit", "dustur-2011", "dustur-2011-fr")):
            ref = os.path.join(REPO, "skills", skill, "references")
            n = lambda s: json.load(open(os.path.join(ref, s, "meta.json"), encoding="utf-8"))["n_articles"]
            self.assertEqual(n(ar), n(fr), ar)

    def test_french_article_search_and_warning(self):
        code, out, _ = self.law("maroc-famille", "article", "mudawwanat-usra-fr", "19")
        self.assertEqual(code, 0)
        self.assertIn("dix-huit ans grégoriens révolus", out)
        self.assertIn("qui fait foi", out)
        code, out, _ = self.law("maroc-travail", "search", "preavis", "licenciement", "--text", "mudawwanat-shughl-fr")
        self.assertEqual(code, 0)                         # accent-insensitive
        self.assertIn("Article", out)

    def test_bare_name_prefers_arabic(self):
        code, out, _ = self.law("maroc-famille", "article", "mudawwanat-usra", "19")
        self.assertEqual(code, 0)
        self.assertIn("المادة 19", out)


if __name__ == "__main__":
    unittest.main()
