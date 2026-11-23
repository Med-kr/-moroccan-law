#!/usr/bin/env python3
"""MCP server for the bundled Moroccan legal texts. Standard library only.

Speaks the Model Context Protocol over stdio (newline-delimited JSON-RPC 2.0),
so the same texts that the Claude skills use are available in any MCP client
(Claude Desktop, Cursor, VS Code, ...).

    python3 mcp/server.py                 # run (a client normally starts it)
    python3 mcp/server.py --self-test     # call every tool once and exit
    python3 mcp/server.py --http [--port 8765] [--host 127.0.0.1] [--token SECRET]
                                          # Streamable HTTP transport, endpoint /mcp, for clients
                                          # that take a URL (put HTTPS in front before exposing it)

Client configuration:
    {"mcpServers": {"moroccan-law": {"command": "python3",
                                     "args": ["/absolute/path/to/mcp/server.py"]}}}

The server only reads files under ../skills. The single network action is
`catalog_download`, which fetches one official PDF from adala.justice.gov.ma.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.environ.get("MOROCCAN_LAW_SKILLS_DIR") or os.path.join(os.path.dirname(HERE), "skills")
SERVER = {"name": "moroccan-law", "version": "0.3.0"}
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
RULES = ("Moroccan legal texts extracted from the official PDFs of the Ministry of Justice portal (Adala). "
         "Never quote an article from memory: fetch it with get_article and quote it as returned. "
         "Every answer must give the article number, the text title, the version date shown in the footer "
         "and the official source URL. The Arabic text is the authoritative one. The texts are extracted "
         "automatically and case law is not included: tell the user to check the official PDF before "
         "relying on a provision in court.")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find(rel: str) -> str:
    """tools/<rel> in a checkout, or the copy shipped inside a skill."""
    for cand in (os.path.join(os.path.dirname(HERE), "tools", rel),
                 os.path.join(SKILLS, "maroc-droit", "scripts", rel)):
        if os.path.isfile(cand):
            return cand
    raise FileNotFoundError(rel)


law = _load("law", _find("law.py"))
sys.modules["law"] = law                        # cards.py imports it by name
cards = _load("cards", _find("cards.py"))
catalog = _load("catalog", _find("catalog.py"))
catalog.ROOT = os.path.join(SKILLS, "maroc-droit", "references")


def index() -> dict[str, str]:
    """slug -> references directory of the skill that holds it."""
    out: dict[str, str] = {}
    if not os.path.isdir(SKILLS):
        return out
    for skill in sorted(os.listdir(SKILLS)):
        ref = os.path.join(SKILLS, skill, "references")
        if not os.path.isdir(ref):
            continue
        for slug in sorted(os.listdir(ref)):
            if os.path.isfile(os.path.join(ref, slug, "text.md")):
                out.setdefault(slug, ref)
    return out


class ToolError(Exception):
    pass


def _run(fn, *args) -> str:
    """Run a command-line function of law.py / catalog.py and capture what it prints."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            fn(*args)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    text = (out.getvalue() + err.getvalue()).strip()
    if code not in (0, 3):                # 3 = "not found", still a useful answer
        raise ToolError(text or f"exit code {code}")
    return text


def _slug(name: str) -> tuple[str, str]:
    idx = index()
    if name in idx:
        return name, idx[name]
    cands = [s for s in idx if s.startswith(name)] or [s for s in idx if name in s]
    if len(cands) > 1:
        cands = [s for s in cands if not s.endswith("-fr")] or cands
    if len(cands) == 1:
        return cands[0], idx[cands[0]]
    raise ToolError(f"unknown or ambiguous text '{name}'. Call list_texts. Close matches: {', '.join(cands) or 'none'}")


def t_list_texts(a: dict) -> str:
    """Reviewed texts; with "title_words", every text (extended corpus included) whose title
    contains them."""
    q = law.keys(str(a.get("title_words") or ""))
    rows = []
    for slug, ref in index().items():
        corpus = os.sep + "maroc-corpus" + os.sep in ref + os.sep
        if corpus and not q:
            continue
        m = json.load(open(os.path.join(ref, slug, "meta.json"), encoding="utf-8"))
        if q:
            tk = set(law.keys(f"{m.get('title', '')} {m.get('source_title', '')} {m.get('title_fr', '')}"))
            tk |= {v for k in tk for v in law.variants(k)}
            if not all(x in tk for x in q):
                continue
        rows.append(f"{slug}\t{os.path.basename(os.path.dirname(ref))}\t{m['n_articles']} {m['article_keyword']}"
                    f"\t{m.get('consolidated_on') or '-'}\t{m['title']}\t{m.get('title_fr', '')}")
    head = "text\tskill\tarticles\tversion\ttitle\ttitle_fr\n"
    if not q:
        head = ("# reviewed texts; 800+ more laws (maroc-corpus, automatic extraction) are found with "
                "title_words, e.g. title_words='التعليم'\n") + head
    return head + ("\n".join(rows) or "(no text title contains these words)")


def t_get_article(a: dict) -> str:
    slug, ref = _slug(str(a["text"]))
    nums = a.get("numbers") or []
    if isinstance(nums, (str, int)):
        nums = [nums]
    if not nums:
        raise ToolError("numbers is required, e.g. [\"43\"], [\"43..47\"], [\"65-2\"]")
    law.ROOT = ref
    return _run(law.cmd_article, slug, [str(n) for n in nums])


def t_article_card(a: dict) -> str:
    slug, ref = _slug(str(a["text"]))
    law.ROOT = ref
    cards.law.ROOT = ref
    c = cards.card(slug, str(a["number"]))
    return json.dumps(c, ensure_ascii=False, indent=1)


def t_search_articles(a: dict) -> str:
    words = str(a["query"]).split()
    if not words:
        raise ToolError("query is empty")
    limit = int(a.get("max_results") or 10)
    any_ = bool(a.get("any_word"))
    if a.get("text"):
        slug, ref = _slug(str(a["text"]))
        law.ROOT = ref
        return _run(law.cmd_search, words, slug, limit, any_)
    chunks = []
    for ref in sorted(set(index().values())):
        if os.sep + "maroc-corpus" + os.sep in ref + os.sep:
            continue        # 800+ texts of the extended corpus: searched only with "text" set
        law.ROOT = ref
        try:
            r = _run(law.cmd_search, words, None, limit, any_)
        except ToolError:
            continue
        if r and not r.startswith("no article matches"):
            chunks.append(r)
    return "\n\n".join(chunks) or "no article matches. Try fewer or different words, or any_word=true."


def t_table_of_contents(a: dict) -> str:
    slug, ref = _slug(str(a["text"]))
    with open(os.path.join(ref, slug, "toc.md"), encoding="utf-8") as fh:
        return fh.read()


def t_text_info(a: dict) -> str:
    slug, ref = _slug(str(a["text"]))
    with open(os.path.join(ref, slug, "meta.json"), encoding="utf-8") as fh:
        return fh.read()


def t_catalog_search(a: dict) -> str:
    argv = ["search", *str(a["query"]).split(), "--max", str(int(a.get("max_results") or 15))]
    if a.get("lang") in ("ar", "fr"):
        argv += ["--lang", a["lang"]]
    if a.get("any_word"):
        argv.append("--any")
    return _run(catalog.main, argv)


def t_catalog_show(a: dict) -> str:
    return _run(catalog.main, ["show", str(a["id"])])


def t_catalog_download(a: dict) -> str:
    return _run(catalog.main, ["get", str(a["id"])])


S = lambda props, req: {"type": "object", "properties": props, "required": req, "additionalProperties": False}
TEXT = {"type": "string", "description": "Text identifier from list_texts (a unique prefix works), e.g. 'mudawwanat-usra'."}
TOOLS = [
    ("list_texts", "List the Moroccan legal texts available article by article (identifier, domain, number of "
     "articles, date of the consolidated version, Arabic and French titles). Call this first. Without arguments: the "
     "reviewed texts; with title_words (Arabic words of a law's title, or its number such as '51.17'): every text "
     "whose title contains them, including 800+ laws of the extended corpus (automatic extraction, not reviewed).",
     S({"title_words": {"type": "string"}}, []), t_list_texts),
    ("get_article", "Exact official Arabic text of one or more articles, with footnotes (amendments), version date "
     "and official source URL. Numbers accept ranges '43..47', sub-articles '65-2' or '4.1', and '85 مكرر'.",
     S({"text": TEXT, "numbers": {"type": "array", "items": {"type": "string"}, "minItems": 1}}, ["text", "numbers"]),
     t_get_article),
    ("article_card", "Status card of one article: in force as printed / amended / replaced / added / repealed, the "
     "amending laws with their Bulletin officiel issue and date, articles it refers to, divergence with the other "
     "language version, documented source errors. Read it before relying on an article.",
     S({"text": TEXT, "number": {"type": "string"}}, ["text", "number"]), t_article_card),
    ("search_articles", "Find articles that contain the given Arabic words (hamza, ta-marbuta and diacritics are "
     "ignored). Searches one text, or every text when 'text' is omitted. Returns article numbers with a snippet; "
     "call get_article for the full text.",
     S({"query": {"type": "string", "description": "Arabic words, space-separated; all must appear unless any_word."},
        "text": TEXT, "max_results": {"type": "integer", "minimum": 1, "maximum": 100},
        "any_word": {"type": "boolean"}}, ["query"]), t_search_articles),
    ("table_of_contents", "Structure of a text (books, titles, chapters) with article ranges.",
     S({"text": TEXT}, ["text"]), t_table_of_contents),
    ("text_info", "Source URL, checksum of the official PDF, version date and extraction notes of a text.",
     S({"text": TEXT}, ["text"]), t_text_info),
    ("catalog_search", "Search the catalog of every text published on the Ministry of Justice portal "
     "(laws, dahirs, decrees, orders; Arabic and French) by title words or number such as '31.08'.",
     S({"query": {"type": "string"}, "lang": {"type": "string", "enum": ["ar", "fr"]},
        "max_results": {"type": "integer", "minimum": 1, "maximum": 100}, "any_word": {"type": "boolean"}},
       ["query"]), t_catalog_search),
    ("catalog_show", "Full catalog record of one text, including the URL of its official PDF.",
     S({"id": {"type": "integer"}}, ["id"]), t_catalog_show),
    ("catalog_download", "Download the official PDF of one catalog text from adala.justice.gov.ma and return its "
     "local path.", S({"id": {"type": "integer"}}, ["id"]), t_catalog_download),
]
BY_NAME = {t[0]: t for t in TOOLS}


def handle(msg: dict) -> dict | None:
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:                          # notification: nothing to answer
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    if method == "initialize":
        want = params.get("protocolVersion")
        return ok({"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                   "capabilities": {"tools": {}}, "serverInfo": SERVER, "instructions": RULES})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [{"name": n, "description": d, "inputSchema": s,
                              "annotations": {"readOnlyHint": n != "catalog_download"}} for n, d, s, _ in TOOLS]})
    if method == "tools/call":
        tool = BY_NAME.get(params.get("name"))
        if not tool:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {params.get('name')}"}}
        try:
            text, bad = tool[3](params.get("arguments") or {}), False
        except (ToolError, KeyError, ValueError, OSError) as exc:
            text, bad = f"error: {exc}", True
        return ok({"content": [{"type": "text", "text": text}], "isError": bad})
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}


def serve() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def serve_http(host: str, port: int, token: str | None) -> None:
    """MCP "Streamable HTTP" transport: one endpoint, /mcp, JSON-RPC in a POST body, JSON answer.
    For clients that only take a URL (ChatGPT connectors, hosted agents). Single-threaded on
    purpose (the lookup tools are not thread-safe). Binds to localhost by default; put it behind
    HTTPS (a reverse proxy or a tunnel) and set --token before exposing it."""
    import http.server

    BY_NAME.pop("catalog_download", None)      # a remote client must not write files on this machine
    TOOLS[:] = [t for t in TOOLS if t[0] != "catalog_download"]
    local = host in ("127.0.0.1", "localhost", "::1")

    class H(http.server.BaseHTTPRequestHandler):
        server_version = "moroccan-law-mcp"

        def _send(self, code: int, body: dict | list | None = None) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else b""
            self.send_response(code)
            if body is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _allowed(self) -> bool:
            origin = self.headers.get("Origin")
            # DNS rebinding: a web page must not reach a server bound to this machine
            if origin and local and not re.match(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$", origin):
                self._send(403, {"error": "origin not allowed"})
                return False
            if token and self.headers.get("Authorization") != f"Bearer {token}":
                self._send(401, {"error": "missing or wrong bearer token"})
                return False
            return True

        def do_GET(self):
            if self.path.rstrip("/") in ("", "/health"):
                return self._send(200, {"status": "ok", "server": SERVER, "endpoint": "/mcp"})
            self.send_response(405)              # no server-initiated stream
            self.send_header("Allow", "POST")
            self.end_headers()

        def do_POST(self):
            if self.path.split("?")[0].rstrip("/") != "/mcp":
                return self._send(404, {"error": "use POST /mcp"})
            if not self._allowed():
                return
            try:
                msg = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"null")
            except (ValueError, json.JSONDecodeError):
                return self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            if isinstance(msg, list):
                replies = [r for r in (handle(m) for m in msg if isinstance(m, dict)) if r is not None]
                return self._send(200, replies) if replies else self._send(202)
            if not isinstance(msg, dict):
                return self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}})
            reply = handle(msg)
            return self._send(202) if reply is None else self._send(200, reply)

        def log_message(self, fmt, *args):        # quiet: one line per request on stderr
            sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    srv = http.server.HTTPServer((host, port), H)
    sys.stderr.write(f"moroccan-law MCP over HTTP on http://{host}:{port}/mcp"
                     f"{' (bearer token required)' if token else ''}\n")
    srv.serve_forever()


def self_test() -> int:
    calls = [("list_texts", {}), ("get_article", {"text": "mudawwanat-shughl", "numbers": ["1"]}),
             ("search_articles", {"query": "الفصل التعسفي", "max_results": 2}),
             ("catalog_search", {"query": "31.08", "max_results": 2})]
    slugs = list(index())
    if slugs:
        calls += [("table_of_contents", {"text": slugs[0]}), ("text_info", {"text": slugs[0]})]
    bad = 0
    for name, args in calls:
        r = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})["result"]
        first = r["content"][0]["text"].splitlines()[0][:90] if r["content"][0]["text"] else ""
        print(("FAIL " if r["isError"] else "ok   ") + f"{name}: {first}")
        bad += r["isError"]
    return 1 if bad else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--http" in sys.argv:
        arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
        serve_http(arg("--host", "127.0.0.1"), int(arg("--port", "8765")),
                   arg("--token", os.environ.get("MOROCCAN_LAW_MCP_TOKEN")))
    else:
        serve()
