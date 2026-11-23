"""moroccan-law web app: the Moroccan legal texts and an AI assistant for a law firm, run locally.

    uvicorn webapp.app:app --host 127.0.0.1 --port 8000        (or: docker compose up)

Data stays in MOROCCAN_LAW_DATA (default ./data-webapp): SQLite, encrypted contents, the firm's
AI key. The only outgoing connections are the AI provider chosen by the firm (with its own key)
and, on request, the official PDF of a text on adala.justice.gov.ma.
"""
from __future__ import annotations

import io
import json
import os
import re

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import agent, documents
from .store import Store

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("MOROCCAN_LAW_DATA") or os.path.join(os.getcwd(), "data-webapp")
COOKIE = "mlaw_session"

store = Store(DATA)
app = FastAPI(title="moroccan-law", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = ("default-src 'self'; img-src 'self' data:; style-src 'self'; "
                                               "script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
    return resp


# ------------------------------------------------------------------------------ auth
def current_user(request: Request) -> dict:
    user = store.user_for(request.cookies.get(COOKIE))
    if not user:
        raise HTTPException(401, "login required")
    return user


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "admin only")
    return user


class Credentials(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=10, max_length=200)


@app.get("/api/status")
def status(request: Request):
    user = store.user_for(request.cookies.get(COOKIE))
    return {"setup_needed": not store.has_users(), "user": user,
            "provider_ready": bool(store.setting("api_key")) or store.setting("provider") == "openai"}


@app.post("/api/setup")
def setup(c: Credentials):
    if store.has_users():
        raise HTTPException(409, "already set up")
    store.add_user(c.name, c.password, "admin")
    store.audit(c.name, "setup", "first administrator created")
    return {"ok": True}


@app.post("/api/login")
def login(c: Credentials, response: Response):
    token = store.login(c.name, c.password)
    store.audit(c.name, "login" if token else "login_failed")
    if not token:
        raise HTTPException(401, "wrong name or password")
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=12 * 3600,
                        secure=os.environ.get("MOROCCAN_LAW_HTTPS") == "1")
    store.purge(int(store.setting("retention_days", 90) or 0))
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    tok = request.cookies.get(COOKIE)
    if tok:
        store.logout(tok)
    response.delete_cookie(COOKIE)
    return {"ok": True}


# ------------------------------------------------------------------------------ administration
class Settings(BaseModel):
    provider: str = Field("anthropic", pattern="^(anthropic|openai)$")
    model: str = Field("", max_length=100)
    effort: str = Field("medium", pattern="^(low|medium|high|xhigh|max)$")
    api_key: str | None = Field(None, max_length=400)      # write-only; None keeps the stored key
    base_url: str = Field("", max_length=300)
    retention_days: int = Field(90, ge=0, le=3650)


@app.get("/api/settings")
def get_settings(user: dict = Depends(admin_user)):
    return {"provider": store.setting("provider", "anthropic"), "model": store.setting("model", agent.DEFAULT_MODEL),
            "effort": store.setting("effort", "medium"), "base_url": store.setting("base_url", ""),
            "retention_days": store.setting("retention_days", 90), "has_key": bool(store.setting("api_key"))}


@app.put("/api/settings")
def put_settings(s: Settings, user: dict = Depends(admin_user)):
    for k in ("provider", "model", "effort", "base_url", "retention_days"):
        store.set_setting(k, getattr(s, k))
    if s.api_key is not None:
        store.set_setting("api_key", s.api_key.strip())
    store.audit(user["name"], "settings", f"provider={s.provider} model={s.model or '-'} retention={s.retention_days}")
    return {"ok": True}


class NewUser(Credentials):
    role: str = Field("member", pattern="^(admin|member)$")


@app.get("/api/users")
def list_users(user: dict = Depends(admin_user)):
    return store.users()


@app.post("/api/users")
def add_user(u: NewUser, user: dict = Depends(admin_user)):
    try:
        store.add_user(u.name, u.password, u.role)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    store.audit(user["name"], "user_add", u.name)
    return {"ok": True}


@app.delete("/api/users/{uid}")
def del_user(uid: int, user: dict = Depends(admin_user)):
    if uid == user["id"]:
        raise HTTPException(400, "cannot delete yourself")
    store.delete_user(uid)
    store.audit(user["name"], "user_delete", str(uid))
    return {"ok": True}


@app.get("/api/audit")
def audit(user: dict = Depends(admin_user)):
    return store.audit_log()


# ------------------------------------------------------------------------------ law (no AI)
def tool(name: str, args: dict) -> str:
    out, err = agent.run_tool(agent.tool_specs([]), name, args)
    if err:
        raise HTTPException(404, out)
    return out


@app.get("/api/texts")
def texts(q: str = "", user: dict = Depends(current_user)):
    return {"text": tool("list_texts", {"title_words": q} if q.strip() else {})}


@app.get("/api/search")
def search(q: str, text: str = "", user: dict = Depends(current_user)):
    args = {"query": q, "max_results": 15}
    if text:
        args["text"] = text
    return {"text": tool("search_articles", args)}


@app.get("/api/article")
def article(text: str, n: str, user: dict = Depends(current_user)):
    body = tool("get_article", {"text": text, "numbers": [n]})
    try:
        card = json.loads(tool("article_card", {"text": text, "number": n}))
    except HTTPException:
        card = None
    return {"text": body, "card": card}


class Deadline(BaseModel):
    start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    days: int = Field(0, ge=0, le=3650)
    months: int = Field(0, ge=0, le=120)
    electronic: bool = False
    holidays: list[str] = []
    restart: str = Field("", pattern=r"^$|^(212|380):\d{4}-\d{2}-\d{2}$")


@app.post("/api/deadline")
def deadline(d: Deadline, user: dict = Depends(current_user)):
    args = {"start": d.start, "electronic": d.electronic, "holidays": d.holidays}
    if d.days:
        args["days"] = d.days
    if d.months:
        args["months"] = d.months
    if d.restart:
        args["restart"] = d.restart
    return {"text": tool("compute_deadline", args)}


# ------------------------------------------------------------------------------ documents and decisions
@app.post("/api/documents")
async def upload(file: UploadFile = File(...), user: dict = Depends(current_user)):
    data = await file.read(documents.MAX_BYTES + 1)
    try:
        text = documents.extract(file.filename or "document", data)
    except Exception as exc:
        raise HTTPException(400, f"cannot read the file: {exc}")
    if not text:
        raise HTTPException(422, "no text in this file (scanned PDF?): provide a PDF with a text layer or a Word file")
    refs = documents.references(text)
    doc_id = store.save_document(user["id"], file.filename or "document", text, refs)
    store.audit(user["name"], "document_upload", f"id={doc_id} chars={len(text)}")
    return {"id": doc_id, "name": file.filename, "chars": len(text), "refs": refs, "excerpt": text[:600]}


@app.get("/api/documents")
def list_documents(user: dict = Depends(current_user)):
    return store.documents(user["id"])


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, user: dict = Depends(current_user)):
    store.delete_document(user["id"], doc_id)
    store.audit(user["name"], "document_delete", str(doc_id))
    return {"ok": True}


class Decision(BaseModel):
    ref: str = Field(min_length=3, max_length=300)
    text: str = Field(min_length=20, max_length=200_000)


@app.post("/api/decisions")
def add_decision(d: Decision, user: dict = Depends(current_user)):
    refs = documents.references(d.text)
    did = store.save_decision(user["id"], d.ref, d.text, refs["articles"])
    store.audit(user["name"], "decision_add", f"id={did}")
    return {"id": did, "articles": refs["articles"], "laws": refs["laws"]}


@app.get("/api/decisions")
def list_decisions(user: dict = Depends(current_user)):
    return [{k: v for k, v in d.items() if k != "text"} | {"excerpt": d["text"][:300]} for d in store.decisions(user["id"])]


@app.delete("/api/decisions/{did}")
def delete_decision(did: int, user: dict = Depends(current_user)):
    store.delete_decision(user["id"], did)
    return {"ok": True}


def user_tools(user: dict) -> list:
    """Tools over the firm's own material, scoped to the user who asks."""
    S = agent.S

    def read_document(a: dict) -> str:
        d = store.document(user["id"], int(a["id"]))
        if not d:
            return "document not found"
        return f"# {d['name']}\nreferences found: {json.dumps(d['refs'], ensure_ascii=False)}\n\n{d['text'][:150000]}"

    def my_decisions(a: dict) -> str:
        words = [w for w in str(a.get("query", "")).split() if w]
        rows = []
        for d in store.decisions(user["id"]):
            if not words or all(w in d["text"] or w in d["ref"] for w in words):
                rows.append(f"## {d['ref']}\narticles cited: {', '.join(d['articles']) or '-'}\n{d['text'][:4000]}")
        return "\n\n".join(rows[:5]) or "no decision in the firm's library matches"

    return [("read_document", "Full text of a document the user uploaded (id given in the conversation), with "
             "the laws and articles it cites. Confidential client material.",
             S({"id": {"type": "integer"}}, ["id"]), read_document),
            ("my_decisions", "Court decisions the firm saved in its own library (pasted by its lawyers), searched "
             "by words. The only case law available: cite it with its reference as saved.",
             S({"query": {"type": "string"}}, []), my_decisions)]


# ------------------------------------------------------------------------------ chat
class Ask(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    conversation_id: int | None = None
    document_ids: list[int] = []


def provider_cfg() -> dict:
    return {"provider": store.setting("provider", "anthropic"), "model": store.setting("model", "") or None,
            "effort": store.setting("effort", "medium"), "api_key": store.setting("api_key", ""),
            "base_url": store.setting("base_url", "")}


@app.post("/api/chat")
async def chat(a: Ask, user: dict = Depends(current_user)):
    cfg = provider_cfg()
    if cfg["provider"] == "anthropic" and not cfg["api_key"]:
        raise HTTPException(400, "no AI key: an administrator must enter the firm's key in Settings")
    conv = store.conversation(user["id"], a.conversation_id) if a.conversation_id else None
    record = conv if isinstance(conv, dict) else {"display": [], "raw": [], "provider": cfg["provider"]}
    if record.get("provider") != cfg["provider"]:          # provider changed: keep the text, restart the raw history
        record["raw"] = [{"role": m["role"], "content": m["text"]} for m in record["display"] if m.get("text")]
        record["provider"] = cfg["provider"]
    text = a.message
    docs = [store.document(user["id"], i) for i in a.document_ids]
    docs = [d for d in docs if d]
    if docs:
        text += "\n\n[" + "; ".join(f"document id={d['id']}: {d['name']}" for d in docs) + " — use read_document]"
    record["raw"].append({"role": "user", "content": text})
    record["display"].append({"role": "user", "text": a.message, "documents": [d["name"] for d in docs]})
    specs = agent.tool_specs(user_tools(user))
    store.audit(user["name"], "chat", f"conversation={a.conversation_id or 'new'} chars={len(a.message)}")

    async def events():
        answer, sources, notices = [], [], []
        try:
            async for ev in agent.run_turn(cfg, record["raw"], specs):
                if ev["type"] == "text":
                    answer.append(ev["text"])
                elif ev["type"] == "source":
                    sources.append({k: ev[k] for k in ("text", "article", "law", "url")})
                elif ev["type"] in ("notice", "error"):
                    notices.append(ev["message"])
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            record["display"].append({"role": "assistant", "text": "".join(answer), "sources": sources, "notices": notices})
            cid = store.save_conversation(user["id"], a.conversation_id, a.message, record)
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': cid})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})


@app.get("/api/conversations")
def conversations(user: dict = Depends(current_user)):
    return store.conversations(user["id"])


@app.get("/api/conversations/{cid}")
def conversation(cid: int, user: dict = Depends(current_user)):
    rec = store.conversation(user["id"], cid)
    if rec is None:
        raise HTTPException(404, "not found")
    return {"id": cid, "messages": rec.get("display", []) if isinstance(rec, dict) else []}


@app.delete("/api/conversations/{cid}")
def delete_conversation(cid: int, user: dict = Depends(current_user)):
    store.delete_conversation(user["id"], cid)
    store.audit(user["name"], "conversation_delete", str(cid))
    return {"ok": True}


@app.get("/api/conversations/{cid}/export.docx")
def export_docx(cid: int, user: dict = Depends(current_user)):
    import docx
    from docx.shared import Pt

    rec = store.conversation(user["id"], cid)
    if not isinstance(rec, dict):
        raise HTTPException(404, "not found")
    d = docx.Document()
    d.add_heading("moroccan-law — consultation des textes", level=1)
    for m in rec["display"]:
        d.add_heading("Question" if m["role"] == "user" else "Réponse", level=2)
        for para in (m.get("text") or "").split("\n"):
            p = d.add_paragraph(para)
            if re.search(r"[؀-ۿ]", para):
                p.paragraph_format.alignment = 2          # right-aligned for Arabic
            for r in p.runs:
                r.font.size = Pt(11)
        for s in m.get("sources") or []:
            d.add_paragraph(f"Source : {s['law']} — article {s['article']} — {s.get('url') or ''}", style="List Bullet")
    d.add_paragraph("Information juridique fondée sur les textes officiels publiés sur Adala ; ce n'est pas une "
                    "consultation. Vérifier le PDF officiel avant tout dépôt.").runs[0].italic = True
    buf = io.BytesIO()
    d.save(buf)
    store.audit(user["name"], "export_docx", str(cid))
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="consultation-{cid}.docx"'})


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "static", "index.html"))
