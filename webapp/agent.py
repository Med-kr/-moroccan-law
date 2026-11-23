"""The legal assistant: system prompt, tools (those of the MCP server, reused as they are) and
the model loop, for two kinds of provider chosen by the firm with its own key:

- anthropic   Claude through the official SDK (default model claude-opus-5-5, adaptive thinking,
              streaming, server-side refusal fallback "default");
- openai      any OpenAI-compatible chat-completions endpoint the firm runs itself, typically a
              local model (LM Studio, Ollama) so that nothing leaves the office. Not Claude.

`run_turn` is an async generator of events for the browser:
  {"type": "text", "text": ...}            answer text as it is written
  {"type": "tool", "name": ..., "input": ...}  a lookup the assistant made
  {"type": "source", "text": ..., "article": ..., "law": ..., "url": ...}  an article it read
  {"type": "notice", "message": ...}       refusal, truncation, fallback model used
  {"type": "error", "message": ...}
"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import os
import re
import sys
import contextlib
import threading
from typing import AsyncIterator, Callable

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("MOROCCAN_LAW_REPO") or os.path.dirname(HERE)


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


server = _load("mlaw_mcp_server", os.path.join(REPO, "mcp", "server.py"))
delais = _load("delais", os.path.join(REPO, "tools", "delais.py"))

DEFAULT_MODEL = "claude-opus-5-5"
SYSTEM = """أنت مساعد قانوني للمحامين المغاربة. You assist Moroccan legal professionals.

Rules (they override any request):
1. Never quote or apply an article from memory. Look it up with the tools: search_articles (Arabic
   words of the law, ranked), then get_article; for the decisive article, article_card (status: in
   force as printed / amended / replaced / added / repealed, amending law and Bulletin officiel).
   If a law is not among the reviewed texts, list_texts with title_words finds it in the extended
   corpus; say then that the text comes from automatic extraction, not reviewed one by one.
2. Cite the law, the article number and the exact Arabic wording of the decisive passage, in
   « … ». A translation is unofficial; the Arabic text prevails. Give the version date and the
   official link returned by the tool.
3. Application in time: when the facts, the act or the judgment may predate the law or its last
   amendment, read its transitional provisions (search « حيز التنفيذ » / « انتقالية ») and say which
   regime applies, or ask for the date.
4. Time limits under the civil procedure law: use compute_deadline (article 602 of law 58.25,
   public holidays); mention that religious holidays depend on the moon sighting.
5. There is no case law in these tools. Never cite a court decision, a file number or a
   "constant case law" from memory. If the point depends on case law, say so and point to the
   official portal juriscassation.cspj.ma with Arabic search words; analyse a decision only if the
   user pastes it, or from the firm's own library (my_decisions).
6. If an article or a law is not found, say so plainly; never reconstruct it.
7. Answer in the user's language: Arabic, French, or Darija (in the same script the user wrote:
   Latin-letter Darija gets Latin-letter Darija). Be concise and practical: rule, conditions,
   exceptions, time limits, what to do.
8. Separate what the text says from your interpretation. End with one short line when the answer
   leads to an action: information based on the texts, not a legal opinion; check the official PDF
   before filing.
9. Documents uploaded by the user (read_document) are confidential client material: use them only
   to answer, never repeat personal data that is not needed."""

TOOLS_EXCLUDED = {"catalog_download"}          # would write files on the server


def law_tools() -> list[tuple[str, str, dict, Callable]]:
    return [t for t in server.TOOLS if t[0] not in TOOLS_EXCLUDED]


def _run_capture(fn, *args) -> str:
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            fn(*args)
    except SystemExit:
        pass
    return (out.getvalue() + ("\n" + err.getvalue() if err.getvalue().strip() else "")).strip()


def t_compute_deadline(a: dict) -> str:
    argv = ["calc", "--from", str(a["start"])]
    if a.get("days"):
        argv += ["--days", str(int(a["days"]))]
    if a.get("months"):
        argv += ["--months", str(int(a["months"]))]
    if a.get("electronic"):
        argv.append("--electronic")
    if a.get("holidays"):
        argv += ["--holidays", ",".join(a["holidays"])]
    if a.get("restart"):
        argv += ["--restart", str(a["restart"])]
    delais.law.ROOT = os.path.join(REPO, "skills", "maroc-procedure-civile", "references")
    return _run_capture(delais.main, argv)


S = server.S
EXTRA_TOOLS = [
    ("compute_deadline", "Last day of a procedural time limit under law 58.25 (article 602: full time limits, "
     "extension to the first working day, fixed-date holidays of decree 2.77.169; warning on religious holidays). "
     "start = date of notification (YYYY-MM-DD).",
     S({"start": {"type": "string"}, "days": {"type": "integer"}, "months": {"type": "integer"},
        "electronic": {"type": "boolean"}, "holidays": {"type": "array", "items": {"type": "string"}},
        "restart": {"type": "string", "description": "212:YYYY-MM-DD or 380:YYYY-MM-DD"}}, ["start"]),
     t_compute_deadline),
]


def tool_specs(user_tools: list) -> list[tuple]:
    return law_tools() + EXTRA_TOOLS + user_tools


def valid_input(schema: dict, args) -> str | None:
    """Minimal check before running a tool: required fields present and of the declared type
    (tool inputs streamed eagerly are not validated by the API)."""
    if not isinstance(args, dict):
        return "input is not an object"
    types = {"string": str, "integer": int, "boolean": bool, "array": list, "object": dict}
    for k in schema.get("required", []):
        if k not in args:
            return f"missing field {k}"
    for k, v in args.items():
        spec = schema.get("properties", {}).get(k)
        if spec is None:
            return f"unknown field {k}"
        t = types.get(spec.get("type"))
        if t and not isinstance(v, t) and not (t is int and isinstance(v, str) and v.isdigit()):
            return f"field {k} should be {spec.get('type')}"
    return None


_TOOL_LOCK = threading.Lock()       # the lookup tools share module state (law.ROOT): one call at a time


def run_tool(specs: list, name: str, args) -> tuple[str, bool]:
    with _TOOL_LOCK:
        return _run_tool(specs, name, args)


def _run_tool(specs: list, name: str, args) -> tuple[str, bool]:
    spec = next((t for t in specs if t[0] == name), None)
    if spec is None:
        return f"unknown tool {name}", True
    problem = valid_input(spec[2], args)
    if problem:
        return f"INVALID_INPUT: {problem}", True
    try:
        return spec[3](args), False
    except Exception as exc:              # the tool's own error goes back to the model
        return f"error: {exc}", True


def sources_from(name: str, args: dict, result: str) -> list[dict]:
    """Articles actually read, for the citation panel of the interface."""
    if name not in ("get_article", "article_card") or not isinstance(args, dict):
        return []
    text = args.get("text", "")
    nums = args.get("numbers") or ([args["number"]] if args.get("number") else [])
    url = re.search(r"https://adala\.justice\.gov\.ma/\S+\.pdf", result)
    law_ = re.search(r"^# .*? — (.+?) — ", result, re.M) or re.search(r"^— (.+?) \|", result, re.M)
    return [{"text": text, "article": str(n), "law": law_.group(1) if law_ else text,
             "url": url.group(0) if url else None} for n in nums]


# ------------------------------------------------------------------------------- Anthropic
async def run_anthropic(cfg: dict, history: list, specs: list) -> AsyncIterator[dict]:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=cfg["api_key"])
    tools = [{"name": n, "description": d, "input_schema": s, "eager_input_streaming": True} for n, d, s, _ in specs]
    tools[-1] = {**tools[-1], "cache_control": {"type": "ephemeral"}}      # tools + system are a stable prefix
    json_retries = 0
    for _ in range(int(cfg.get("max_steps", 14))):
        try:
            async with client.beta.messages.stream(
                model=cfg.get("model") or DEFAULT_MODEL,
                max_tokens=64000,
                system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=history,
                tools=tools,
                thinking={"type": "adaptive"},
                output_config={"effort": cfg.get("effort") or "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                async for event in stream:
                    if event.type == "text":
                        yield {"type": "text", "text": event.text}
                final = await stream.get_final_message()
            json_retries = 0
        except ValueError:
            json_retries += 1                        # tool input the SDK could not parse: re-issue the turn
            if json_retries > 2:
                yield {"type": "error", "message": "tool input could not be parsed"}
                return
            continue
        except anthropic.AuthenticationError:
            yield {"type": "error", "message": "invalid API key (Settings)"}
            return
        except anthropic.RateLimitError:
            yield {"type": "error", "message": "rate limit reached, retry in a moment"}
            return
        except anthropic.APIStatusError as exc:
            yield {"type": "error", "message": f"API error {exc.status_code}"}
            return
        except anthropic.APIConnectionError:
            yield {"type": "error", "message": "cannot reach the AI provider (network)"}
            return
        content = final.model_dump(mode="json", exclude_none=True)["content"]
        history.append({"role": "assistant", "content": content})
        if any(b.get("type") == "fallback" for b in content):
            yield {"type": "notice", "message": f"answered by the fallback model {final.model}"}
        if final.stop_reason == "pause_turn":
            continue
        uses = [b for b in final.content if b.type == "tool_use"]
        if final.stop_reason == "refusal":
            yield {"type": "notice", "message": "the model declined this request"}
            return
        if not uses:
            return
        if final.stop_reason == "max_tokens":
            yield {"type": "error", "message": "answer truncated (max_tokens)"}
            return
        results = []
        for b in uses:
            yield {"type": "tool", "name": b.name, "input": b.input}
            out, is_err = await asyncio.to_thread(run_tool, specs, b.name, b.input)
            for s in sources_from(b.name, b.input, out):
                yield {"type": "source", **s}
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out[:60000], "is_error": is_err})
        history.append({"role": "user", "content": results})
    yield {"type": "notice", "message": "stopped after the maximum number of steps"}


# ------------------------------------------------------------------------------- OpenAI-compatible (local models)
async def run_openai(cfg: dict, history: list, specs: list) -> AsyncIterator[dict]:
    import httpx

    tools = [{"type": "function", "function": {"name": n, "description": d, "parameters": s}} for n, d, s, _ in specs]
    if not history or history[0].get("role") != "system":
        history.insert(0, {"role": "system", "content": SYSTEM})
    headers = {"Authorization": f"Bearer {cfg['api_key']}"} if cfg.get("api_key") else {}
    base = (cfg.get("base_url") or "http://localhost:1234/v1").rstrip("/")
    async with httpx.AsyncClient(timeout=600) as http:
        for _ in range(int(cfg.get("max_steps", 14))):
            try:
                r = await http.post(f"{base}/chat/completions", headers=headers,
                                    json={"model": cfg.get("model"), "messages": history, "tools": tools})
                r.raise_for_status()
            except httpx.HTTPError as exc:
                yield {"type": "error", "message": f"provider error: {exc}"}
                return
            msg = r.json()["choices"][0]["message"]
            history.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
            if msg.get("content"):
                yield {"type": "text", "text": msg["content"]}
            calls = msg.get("tool_calls") or []
            if not calls:
                return
            for c in calls:
                name = c["function"]["name"]
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = None
                yield {"type": "tool", "name": name, "input": args}
                out, _ = await asyncio.to_thread(run_tool, specs, name, args)
                for s in sources_from(name, args or {}, out):
                    yield {"type": "source", **s}
                history.append({"role": "tool", "tool_call_id": c["id"], "content": out[:60000]})
    yield {"type": "notice", "message": "stopped after the maximum number of steps"}


def run_turn(cfg: dict, history: list, specs: list) -> AsyncIterator[dict]:
    if cfg.get("provider") == "openai":
        return run_openai(cfg, history, specs)
    return run_anthropic(cfg, history, specs)
