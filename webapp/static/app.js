// moroccan-law web app — no framework, no innerHTML: every text goes through textContent.
const $ = (id) => document.getElementById(id);
let state = { user: null, conversation: null, attached: [], busy: false };

async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {},
    ...opts,
    body: opts.body && !(opts.body instanceof FormData) ? JSON.stringify(opts.body) : opts.body,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch (_) {}
    throw new Error(msg);
  }
  const type = res.headers.get("content-type") || "";
  return type.includes("json") ? res.json() : res;
}

function el(tag, props = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of children) if (c !== null && c !== undefined) e.append(c instanceof Node ? c : document.createTextNode(c));
  return e;
}

// Minimal, safe formatting of the answer: **bold** and line breaks, built as DOM nodes.
function formatted(text) {
  const frag = document.createDocumentFragment();
  text.split(/(\*\*[^*]+\*\*)/g).forEach((part) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) frag.append(el("strong", {}, part.slice(2, -2)));
    else frag.append(document.createTextNode(part));
  });
  return frag;
}

// ---------------------------------------------------------------- auth
async function boot() {
  const s = await api("/api/status");
  state.user = s.user;
  if (!s.user) return showAuth(s.setup_needed);
  $("auth").classList.add("hidden");
  $("main").classList.remove("hidden");
  $("whoami").textContent = `${s.user.name} (${s.user.role})`;
  document.querySelectorAll(".admin-only").forEach((b) => b.classList.toggle("hidden", s.user.role !== "admin"));
  $("provider-warning").classList.toggle("hidden", s.provider_ready);
  loadHistory(); loadDocs();
}

function showAuth(setup) {
  $("main").classList.add("hidden");
  $("auth").classList.remove("hidden");
  $("auth-hint").textContent = setup ? "Première utilisation : créez le compte administrateur du cabinet." : "";
  $("auth-submit").textContent = setup ? "Créer l'administrateur" : "Se connecter";
  $("auth-form").onsubmit = async (ev) => {
    ev.preventDefault();
    $("auth-error").textContent = "";
    const body = { name: $("auth-name").value.trim(), password: $("auth-pass").value };
    try {
      if (setup) await api("/api/setup", { method: "POST", body });
      await api("/api/login", { method: "POST", body });
      boot();
    } catch (e) { $("auth-error").textContent = e.message; }
  };
}

$("logout").onclick = async () => { await api("/api/logout", { method: "POST" }); location.reload(); };

// ---------------------------------------------------------------- tabs
document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("active", x === b));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("hidden", t.id !== "tab-" + b.dataset.tab));
  if (b.dataset.tab === "settings") loadSettings();
  if (b.dataset.tab === "decisions") loadDecisions();
  if (b.dataset.tab === "docs") loadDocs();
}));

// ---------------------------------------------------------------- history
async function loadHistory() {
  const list = await api("/api/conversations");
  const ul = $("history"); ul.textContent = "";
  for (const c of list) {
    const li = el("li", { class: c.id === state.conversation ? "active" : "", onclick: () => openConversation(c.id) },
      el("span", { dir: "auto" }, c.title),
      el("button", { title: "Supprimer", onclick: async (ev) => {
        ev.stopPropagation();
        if (!confirm("Supprimer cette conversation ?")) return;
        await api(`/api/conversations/${c.id}`, { method: "DELETE" });
        if (state.conversation === c.id) newChat();
        loadHistory();
      } }, "×"));
    ul.append(li);
  }
}

async function openConversation(id) {
  const c = await api(`/api/conversations/${id}`);
  state.conversation = id;
  $("messages").textContent = "";
  for (const m of c.messages) renderMessage(m);
  addExport();
  loadHistory();
}

function newChat() { state.conversation = null; $("messages").textContent = ""; state.attached = []; renderAttached(); loadHistory(); }
$("new-chat").onclick = newChat;

function addExport() {
  if (!state.conversation) return;
  $("messages").append(el("div", { class: "meta" },
    el("a", { href: `/api/conversations/${state.conversation}/export.docx` }, "Exporter en Word"),
    " · ",
    el("button", { class: "link", onclick: () => window.print() }, "Imprimer / PDF")));
}

// ---------------------------------------------------------------- chat
function sourceChips(sources) {
  const meta = el("div", { class: "meta" });
  const seen = new Set();
  for (const s of sources || []) {
    const key = s.text + "|" + s.article;
    if (seen.has(key)) continue;
    seen.add(key);
    meta.append(el("span", { class: "chip", dir: "auto", onclick: () => openArticle(s.text, s.article) }, `${s.law} — ${s.article}`));
  }
  return meta;
}

function renderMessage(m) {
  const box = el("div", { class: "msg " + m.role, dir: "auto" });
  if (m.role === "user") {
    box.append(m.text);
    if (m.documents && m.documents.length) box.append(el("div", { class: "meta" }, "📎 " + m.documents.join(", ")));
  } else {
    box.append(formatted(m.text || ""));
    for (const n of m.notices || []) box.append(el("div", { class: "notice" }, n));
    if (m.sources && m.sources.length) box.append(sourceChips(m.sources));
  }
  $("messages").append(box);
  return box;
}

$("ask").onsubmit = async (ev) => {
  ev.preventDefault();
  const q = $("question").value.trim();
  if (!q || state.busy) return;
  state.busy = true; $("send").disabled = true;
  renderMessage({ role: "user", text: q, documents: state.attached.map((d) => d.name) });
  $("question").value = "";
  const box = el("div", { class: "msg assistant", dir: "auto" });
  const tools = el("div", { class: "tools" }, "…");
  const body = el("div");
  box.append(tools, body);
  $("messages").append(box);
  let text = "", sources = [];
  try {
    const res = await fetch("/api/chat", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, conversation_id: state.conversation, document_ids: state.attached.map((d) => d.id) }) });
    if (!res.ok) { const j = await res.json(); throw new Error(j.detail || res.statusText); }
    const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const line = buf.slice(0, i); buf = buf.slice(i + 2);
        if (!line.startsWith("data: ")) continue;
        const ev = JSON.parse(line.slice(6));
        if (ev.type === "text") { text += ev.text; body.textContent = ""; body.append(formatted(text)); }
        else if (ev.type === "tool") tools.textContent = `🔎 ${ev.name} ${JSON.stringify(ev.input)}`;
        else if (ev.type === "source") sources.push(ev);
        else if (ev.type === "notice" || ev.type === "error") box.append(el("div", { class: "notice" }, ev.message));
        else if (ev.type === "done") state.conversation = ev.conversation_id;
      }
      $("messages").scrollTop = $("messages").scrollHeight;
    }
    tools.textContent = "";
    if (sources.length) box.append(sourceChips(sources));
    state.attached = []; renderAttached();
    loadHistory();
  } catch (e) {
    box.append(el("div", { class: "notice" }, e.message));
  } finally { state.busy = false; $("send").disabled = false; }
};

// ---------------------------------------------------------------- article dialog
async function openArticle(text, n) {
  try {
    const r = await api(`/api/article?text=${encodeURIComponent(text)}&n=${encodeURIComponent(n)}`);
    $("ad-title").textContent = `${text} — ${n}`;
    $("ad-text").textContent = r.text;
    const card = r.card;
    $("ad-card").textContent = "";
    if (card) $("ad-card").append(cardNodes(card));
    $("article-dialog").showModal();
  } catch (e) { alert(e.message); }
}
const STATUS_FR = { "repealed": "abrogé", "replaced": "abrogé et remplacé (nouvelle rédaction)", "added": "ajouté par un texte postérieur",
  "amended": "modifié ou complété", "as printed (no amendment noted)": "tel que publié (aucune modification signalée)",
  "no text in this version": "sans texte dans cette version", "not in this version": "absent de cette version" };
// The card as DOM lines; Arabic values are isolated (bdi) so they do not scramble the French line.
function cardNodes(c) {
  const box = document.createDocumentFragment();
  const line = (...parts) => box.append(el("div", {}, ...parts));
  const ar = (t) => el("bdi", { dir: "auto" }, t);
  line("Statut : ", STATUS_FR[c.status] || c.status);
  for (const a of c.amendments || []) {
    const bo = a.bulletin_officiel;
    line(`• ${STATUS_FR[a.kind] || a.kind} par le texte n° ${a.by || "non identifié"}`,
      ...(bo ? [" — BO n° ", bo.issue, " du ", ar(bo.date), `, p. ${bo.page}`] : [" — référence BO non indiquée dans les notes"]));
  }
  for (const w of c.warnings || []) line("⚠ ", ar(w));
  if (c.version) line("Version consolidée : ", ar(c.version.consolidated_on || "non datée dans le PDF"), ` · mise à jour Adala ${c.version.portal_updated}`);
  if (c.counterpart) line(`Version ${c.counterpart.language === "fr" ? "française" : "arabe"} : ${c.counterpart.has_article ? "article présent" : "article absent"}`);
  if (!c.reviewed) line("Texte du corpus étendu (extraction automatique, non relu un par un).");
  return box;
}
$("ad-close").onclick = () => $("article-dialog").close();

// ---------------------------------------------------------------- search tab
$("search-form").onsubmit = async (ev) => {
  ev.preventDefault();
  const t = $("search-text").value.trim();
  try { $("search-out").textContent = (await api(`/api/search?q=${encodeURIComponent($("search-q").value)}${t ? "&text=" + encodeURIComponent(t) : ""}`)).text; }
  catch (e) { $("search-out").textContent = e.message; }
};
$("find-form").onsubmit = async (ev) => {
  ev.preventDefault();
  try { $("search-out").textContent = (await api(`/api/texts?q=${encodeURIComponent($("find-q").value)}`)).text; }
  catch (e) { $("search-out").textContent = e.message; }
};
$("article-form").onsubmit = (ev) => { ev.preventDefault(); openArticle($("art-text").value.trim(), $("art-n").value.trim()); };

// ---------------------------------------------------------------- deadline tab
$("deadline-form").onsubmit = async (ev) => {
  ev.preventDefault();
  const kind = $("dl-restart-kind").value, rd = $("dl-restart-date").value;
  const body = { start: $("dl-start").value, days: +$("dl-days").value || 0, months: +$("dl-months").value || 0,
    electronic: $("dl-elec").checked, holidays: $("dl-hol").value.split(",").map((x) => x.trim()).filter(Boolean),
    restart: kind && rd ? `${kind}:${rd}` : "" };
  try { $("deadline-out").textContent = (await api("/api/deadline", { method: "POST", body })).text; }
  catch (e) { $("deadline-out").textContent = e.message; }
};

// ---------------------------------------------------------------- documents
async function loadDocs() {
  const docs = await api("/api/documents");
  const ul = $("doc-list"); ul.textContent = "";
  const sel = $("attach-select"); sel.textContent = ""; sel.append(el("option", { value: "" }, "Joindre un document…"));
  for (const d of docs) {
    const refs = [...(d.refs.codes || []), ...(d.refs.laws || []).map((l) => "loi " + l)].join(", ");
    ul.append(el("li", {}, el("span", { dir: "auto" }, `${d.name} — ${refs || "aucune référence détectée"}`),
      el("span", {},
        el("button", { class: "link", onclick: () => attach(d) }, "Joindre à la question"),
        el("button", { class: "link", onclick: async () => { await api(`/api/documents/${d.id}`, { method: "DELETE" }); loadDocs(); } }, "Supprimer"))));
    sel.append(el("option", { value: String(d.id) }, d.name));
  }
  sel.onchange = () => { const d = docs.find((x) => String(x.id) === sel.value); if (d) attach(d); sel.value = ""; };
}
function attach(d) {
  if (!state.attached.some((x) => x.id === d.id)) state.attached.push({ id: d.id, name: d.name });
  renderAttached();
  document.querySelector('#tabs button[data-tab="chat"]').click();
}
function renderAttached() {
  const box = $("attached"); box.textContent = "";
  for (const d of state.attached) box.append(el("span", { class: "chip", onclick: () => { state.attached = state.attached.filter((x) => x.id !== d.id); renderAttached(); } }, `📎 ${d.name} ×`));
}
$("upload-form").onsubmit = async (ev) => {
  ev.preventDefault();
  const f = $("upload-file").files[0]; if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  try { await api("/api/documents", { method: "POST", body: fd }); $("upload-file").value = ""; loadDocs(); }
  catch (e) { alert(e.message); }
};

// ---------------------------------------------------------------- decisions library
async function loadDecisions() {
  const list = await api("/api/decisions");
  const ul = $("dec-list"); ul.textContent = "";
  for (const d of list) ul.append(el("li", {}, el("span", { dir: "auto" }, `${d.ref} — articles : ${d.articles.join(", ") || "—"}`),
    el("button", { class: "link", onclick: async () => { await api(`/api/decisions/${d.id}`, { method: "DELETE" }); loadDecisions(); } }, "Supprimer")));
}
$("decision-form").onsubmit = async (ev) => {
  ev.preventDefault();
  try { await api("/api/decisions", { method: "POST", body: { ref: $("dec-ref").value, text: $("dec-text").value } });
    $("dec-ref").value = ""; $("dec-text").value = ""; loadDecisions(); }
  catch (e) { alert(e.message); }
};

// ---------------------------------------------------------------- settings (admin)
async function loadSettings() {
  const s = await api("/api/settings");
  $("set-provider").value = s.provider; $("set-model").value = s.model || ""; $("set-effort").value = s.effort;
  $("set-base").value = s.base_url || ""; $("set-ret").value = s.retention_days;
  $("set-key").placeholder = s.has_key ? "clé enregistrée — laisser vide pour la garder" : "clé du cabinet";
  const users = await api("/api/users");
  const ul = $("user-list"); ul.textContent = "";
  for (const u of users) ul.append(el("li", {}, `${u.name} (${u.role})`,
    el("button", { class: "link", onclick: async () => { if (confirm("Supprimer ?")) { await api(`/api/users/${u.id}`, { method: "DELETE" }); loadSettings(); } } }, "Supprimer")));
  $("audit").textContent = (await api("/api/audit")).map((a) => `${a.at}  ${a.user || "-"}  ${a.action}  ${a.detail || ""}`).join("\n");
}
$("settings-form").onsubmit = async (ev) => {
  ev.preventDefault();
  const body = { provider: $("set-provider").value, model: $("set-model").value.trim(), effort: $("set-effort").value,
    base_url: $("set-base").value.trim(), retention_days: +$("set-ret").value || 0 };
  if ($("set-key").value) body.api_key = $("set-key").value;
  try { await api("/api/settings", { method: "PUT", body }); $("set-key").value = ""; $("settings-msg").textContent = "Enregistré."; boot(); }
  catch (e) { $("settings-msg").textContent = e.message; }
};
$("user-form").onsubmit = async (ev) => {
  ev.preventDefault();
  try { await api("/api/users", { method: "POST", body: { name: $("u-name").value, password: $("u-pass").value, role: $("u-role").value } });
    $("u-name").value = ""; $("u-pass").value = ""; loadSettings(); }
  catch (e) { alert(e.message); }
};

boot();
