"""Web app: accounts, encryption at rest, law endpoints, documents, chat stream, Anthropic loop
(with a simulated client: no network, no key, no cost)."""
import asyncio
import io
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ["MOROCCAN_LAW_DATA"] = tempfile.mkdtemp(prefix="mlaw-test-")

from fastapi.testclient import TestClient  # noqa: E402

from webapp import agent  # noqa: E402
from webapp import app as appmod  # noqa: E402

ADMIN = {"name": "admin", "password": "correct horse battery"}


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(appmod.app)
        if appmod.store.has_users() is False:
            assert cls.c.post("/api/setup", json=ADMIN).status_code == 200
        assert cls.c.post("/api/login", json=ADMIN).status_code == 200


class Accounts(Base):
    def test_login_required(self):
        anon = TestClient(appmod.app)
        self.assertEqual(anon.get("/api/conversations").status_code, 401)
        self.assertEqual(anon.post("/api/login", json={"name": "admin", "password": "wrong password!"}).status_code, 401)

    def test_member_is_not_admin(self):
        self.c.post("/api/users", json={"name": "member1", "password": "member password 1", "role": "member"})
        m = TestClient(appmod.app)
        self.assertEqual(m.post("/api/login", json={"name": "member1", "password": "member password 1"}).status_code, 200)
        self.assertEqual(m.get("/api/settings").status_code, 403)
        self.assertEqual(m.get("/api/audit").status_code, 403)

    def test_security_headers(self):
        r = self.c.get("/")
        self.assertIn("frame-ancestors 'none'", r.headers["content-security-policy"])
        self.assertEqual(r.headers["x-frame-options"], "DENY")


class Encryption(Base):
    def test_key_is_write_only_and_encrypted_at_rest(self):
        self.assertEqual(self.c.put("/api/settings", json={"provider": "anthropic", "model": "claude-opus-5-5",
                                                           "effort": "medium", "api_key": "sk-ant-TESTKEY123",
                                                           "base_url": "", "retention_days": 90}).status_code, 200)
        s = self.c.get("/api/settings").json()
        self.assertTrue(s["has_key"])
        self.assertNotIn("sk-ant-TESTKEY123", json.dumps(s))
        db = sqlite3.connect(os.path.join(os.environ["MOROCCAN_LAW_DATA"], "moroccan-law.db"))
        raw = b"".join(bytes(r[0]) for r in db.execute("SELECT value FROM settings"))
        self.assertNotIn(b"sk-ant-TESTKEY123", raw)
        self.assertEqual(oct(os.stat(os.path.join(os.environ["MOROCCAN_LAW_DATA"], "secret.key")).st_mode & 0o777), "0o600")


class Law(Base):
    def test_search_article_card_deadline(self):
        r = self.c.get("/api/search", params={"q": "أجل الاستئناف", "text": "msm-58-25"}).json()
        self.assertIn("204", r["text"])
        a = self.c.get("/api/article", params={"text": "mudawwanat-shughl", "n": "184"}).json()
        self.assertIn("2288", a["text"])
        self.assertEqual(a["card"]["status"], "as printed (no amendment noted)")
        d = self.c.post("/api/deadline", json={"start": "2026-11-03", "days": 30}).json()
        self.assertIn("4 دجنبر 2026", d["text"])
        t = self.c.get("/api/texts", params={"q": "59.21"}).json()
        self.assertIn("التعليم المدرسي", t["text"])


class Documents(Base):
    def test_upload_docx_detects_references(self):
        import docx
        d = docx.Document()
        d.add_paragraph("حيث إن المدعي يطالب بالتعويض عن الفصل طبقا للمادة 53 من مدونة الشغل والقانون رقم 65.99.")
        buf = io.BytesIO(); d.save(buf)
        r = self.c.post("/api/documents", files={"file": ("requete.docx", buf.getvalue())}).json()
        self.assertIn("mudawwanat-shughl", r["refs"]["codes"])
        self.assertIn("65.99", r["refs"]["laws"])
        self.assertIn("53", r["refs"]["articles"])
        db = sqlite3.connect(os.path.join(os.environ["MOROCCAN_LAW_DATA"], "moroccan-law.db"))
        raw = b"".join(bytes(x[0]) for x in db.execute("SELECT text FROM documents"))
        self.assertNotIn("المدعي".encode(), raw)                        # encrypted at rest
        self.assertEqual(self.c.delete(f"/api/documents/{r['id']}").status_code, 200)

    def test_no_key_no_chat(self):
        fresh = appmod.store.setting("api_key")
        appmod.store.set_setting("api_key", "")
        try:
            self.assertEqual(self.c.post("/api/chat", json={"message": "x"}).status_code, 400)
        finally:
            appmod.store.set_setting("api_key", fresh or "")

    def test_unreadable_file(self):
        r = self.c.post("/api/documents", files={"file": ("x.exe", b"MZ")})
        self.assertEqual(r.status_code, 400)


class Chat(Base):
    def test_stream_saves_and_exports(self):
        async def fake_turn(cfg, history, specs):
            yield {"type": "tool", "name": "get_article", "input": {"text": "msm-58-25", "numbers": ["204"]}}
            yield {"type": "source", "text": "msm-58-25", "article": "204", "law": "58.25", "url": "https://adala.justice.gov.ma/x.pdf"}
            yield {"type": "text", "text": "أجل الاستئناف ثلاثون يوما (المادة 204)."}
        self.c.put("/api/settings", json={"provider": "anthropic", "model": "", "effort": "medium",
                                          "api_key": "sk-ant-fake", "base_url": "", "retention_days": 90})
        orig = agent.run_turn
        agent.run_turn = fake_turn
        try:
            r = self.c.post("/api/chat", json={"message": "ch7al ajal l-isti2naf?"})
        finally:
            agent.run_turn = orig
        events = [json.loads(l[6:]) for l in r.text.split("\n\n") if l.startswith("data: ")]
        self.assertEqual(events[-1]["type"], "done")
        cid = events[-1]["conversation_id"]
        conv = self.c.get(f"/api/conversations/{cid}").json()
        self.assertEqual(conv["messages"][1]["sources"][0]["article"], "204")
        ex = self.c.get(f"/api/conversations/{cid}/export.docx")
        self.assertEqual(ex.status_code, 200)
        self.assertTrue(ex.content[:2] == b"PK")
        log = self.c.get("/api/audit").json()
        self.assertTrue(any(a["action"] == "chat" for a in log))
        self.assertFalse(any("isti2naf" in (a["detail"] or "") for a in log))   # no content in the audit log


# ------------------------------------------------------------------ simulated Anthropic client
class _Block(types.SimpleNamespace):
    pass


class _Final:
    def __init__(self, content, stop_reason):
        self.content, self.stop_reason, self.model = content, stop_reason, "claude-opus-5-5"

    def model_dump(self, **_):
        return {"content": [dict(vars(b)) for b in self.content]}


class _Stream:
    def __init__(self, final, texts):
        self.final, self.texts = final, texts

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        async def gen():
            for t in self.texts:
                yield types.SimpleNamespace(type="text", text=t)
        return gen()

    async def get_final_message(self):
        return self.final


class FakeAnthropic:
    calls = []

    def __init__(self, api_key):
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(stream=self.stream))

    def stream(self, **kw):
        FakeAnthropic.calls.append(kw)
        if len(FakeAnthropic.calls) == 1:
            return _Stream(_Final([_Block(type="tool_use", id="tu1", name="get_article",
                                          input={"text": "msm-58-25", "numbers": ["204"]})], "tool_use"), [])
        return _Stream(_Final([_Block(type="text", text="30 يوما")], "end_turn"), ["30 ", "يوما"])


class AnthropicLoop(unittest.TestCase):
    def test_tool_round_trip(self):
        import anthropic
        orig = anthropic.AsyncAnthropic
        anthropic.AsyncAnthropic = FakeAnthropic
        FakeAnthropic.calls = []
        history = [{"role": "user", "content": "أجل الاستئناف؟"}]

        async def collect():
            return [e async for e in agent.run_anthropic({"api_key": "x"}, history, agent.tool_specs([]))]
        try:
            events = asyncio.run(collect())
        finally:
            anthropic.AsyncAnthropic = orig
        types_ = [e["type"] for e in events]
        self.assertEqual(types_[:2], ["tool", "source"])
        self.assertEqual("".join(e["text"] for e in events if e["type"] == "text"), "30 يوما")
        tool_result = history[2]["content"][0]
        self.assertEqual(tool_result["tool_use_id"], "tu1")
        self.assertIn("ثلاثين", tool_result["content"])                   # the real article text went back
        first = FakeAnthropic.calls[0]
        self.assertEqual(first["model"], "claude-opus-5-5")
        self.assertEqual(first["fallbacks"], "default")
        self.assertTrue(all(t.get("eager_input_streaming") for t in first["tools"]))

    def test_invalid_tool_input_is_refused(self):
        out, err = agent.run_tool(agent.tool_specs([]), "get_article", {"text": "doc"})
        self.assertTrue(err)
        self.assertIn("missing field numbers", out)


if __name__ == "__main__":
    unittest.main()
