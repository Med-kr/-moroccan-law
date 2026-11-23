#!/usr/bin/env python3
"""Presentation PDF for legal experts (French, Arabic quotes), built from the repository data.
    uv run --with weasyprint python docs/brochure/make_presentation.py
Writes docs/moroccan-law-presentation-experts.pdf."""
import json, glob, os, subprocess, sys, html, datetime as dt
FR = lambda n: f"{n:,}".replace(",", "\u202f")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "docs", "moroccan-law-presentation-experts.pdf")
E = html.escape
cfg = json.load(open(f"{REPO}/countries/ma/skills.json", encoding="utf-8"))

def metas(skill):
    return [json.load(open(m, encoding="utf-8")) for m in glob.glob(f"{REPO}/skills/{skill}/references/*/meta.json")]

def run(skill, script, *a):
    return subprocess.run([sys.executable, f"{REPO}/skills/{skill}/scripts/{script}", *a], capture_output=True, text=True).stdout

# --- skills table
rows = []
tot_t = tot_a = 0
for s in cfg["skills"]:
    ms = metas(s["name"])
    n, a = len(ms), sum(m["n_articles"] for m in ms)
    tot_t += n; tot_a += a
    if s.get("auto"):
        main = "718 lois et dahirs : santé, enseignement, fonction publique, agriculture, élections, collectivités territoriales, énergie, pêche, institutions…"
    else:
        ar = [m for m in ms if m.get("language") != "fr" and "mansukh" not in m["slug"]]
        ar.sort(key=lambda m: -m["n_articles"])
        main = " · ".join(E(m.get("title_fr") or m["title"]) for m in ar[:4]) + (" …" if len(ar) > 4 else "")
    rows.append(f"<tr><td class='code'>{E(s['name'])}</td><td>{E(s['title_fr'])}<div class='ar small'>{E(s['title_ar'])}</div></td>"
                f"<td class='small'>{main}</td><td class='num'>{n}</td><td class='num'>{FR(a)}</td></tr>")
skills_table = "\n".join(rows)

# --- real example
art = run("maroc-procedure-civile", "law.py", "article", "msm-58-25", "204")
art_body = [l for l in art.splitlines() if l and not l.startswith(("##", "(", "—"))][:3]
delais = run("maroc-procedure-civile", "delais.py", "calc", "--from", "2026-11-03", "--days", "30")
del_lines = [l.replace("==>", "").strip() for l in delais.splitlines() if l.strip() and not l.startswith("—")][:6]

# --- reviewed texts with their version dates (annex A)
import re as _re
_MOIS = {"يناير": "janvier", "فبراير": "février", "مارس": "mars", "أبريل": "avril", "ابريل": "avril", "ماي": "mai",
         "مايو": "mai", "يونيو": "juin", "يوليو": "juillet", "يوليوز": "juillet", "غشت": "août", "أغسطس": "août",
         "شتنبر": "septembre", "سبتمبر": "septembre", "أكتوبر": "octobre", "نونبر": "novembre", "نوفمبر": "novembre",
         "دجنبر": "décembre", "ديسمبر": "décembre"}


def fr_date(d):
    if not d:
        return "—"
    m = _re.match(r"^\s*(\d{1,2})\s+(\S+)\s+(\d{4})\s*$", d)
    return f"{m.group(1)} {_MOIS.get(m.group(2), m.group(2))} {m.group(3)}" if m else d


def clean_title(t):
    return _re.sub(r"^\[[^\]]*\]\s*", "", t or "").strip()

rev_rows = []
for s_ in cfg["skills"]:
    if s_.get("auto"):
        continue
    for m in sorted(metas(s_["name"]), key=lambda m: (m.get("language") == "fr", -m["n_articles"])):
        name = E(clean_title(m.get("title_fr") or m["title"]))
        lang = "FR" if m.get("language") == "fr" else "AR"
        rep = " (abrogé)" if "mansukh" in m["slug"] else ""
        rev_rows.append(f"<tr><td class='code'>{E(s_['name'].replace('maroc-', ''))}</td><td>{name}{rep}<div class='ar small'>{E(clean_title(m['title']))}</div></td>"
                        f"<td>{lang}</td><td class='num'>{FR(m['n_articles'])}</td><td class='num'>{E(fr_date(m.get('consolidated_on')))}</td>"
                        f"<td class='num'>{(m.get('source_updated_at') or '')[:10]}</td></tr>")
rev_table = "\n".join(rev_rows)

# --- review sheet
qs = json.load(open(f"{REPO}/evals/legal/questions.json", encoding="utf-8")) + json.load(open(f"{REPO}/evals/legal/holdout.json", encoding="utf-8"))
sheet = "\n".join(f"<tr><td>{q['id']}</td><td>{E(q['skill'].replace('maroc-',''))}</td><td>{E(q['q'])}</td><td class='small'>{E(q['text'])} — art. {E(', '.join(q['art']))}</td><td></td><td></td></tr>" for q in qs)

today = dt.date.today().strftime("%d/%m/%Y")
doc = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>moroccan-law — présentation aux experts</title>
<style>
@page {{ size: A4; margin: 18mm 17mm 20mm 17mm;
  @bottom-left {{ content: "moroccan-law · présentation aux experts"; font: 8pt 'Noto Sans'; color:#777 }}
  @bottom-right {{ content: counter(page) " / " counter(pages); font: 8pt 'Noto Sans'; color:#777 }} }}
@page cover {{ margin: 0; @bottom-left {{ content: none }} @bottom-right {{ content: none }} }}
body {{ font-family: 'Noto Serif', serif; font-size: 10pt; line-height: 1.45; color:#1d1d1d }}
h1,h2,h3 {{ font-family:'Noto Sans', sans-serif; color:#0b4d34 }}
h2 {{ font-size: 15pt; border-bottom: 2px solid #c1272d; padding-bottom: 3px; margin-top: 0; page-break-after: avoid }}
h3 {{ font-size: 11pt; margin: 14px 0 4px }}
.ar {{ font-family: 'Noto Naskh Arabic', serif; direction: rtl; text-align: right }}
bdi.ar {{ unicode-bidi: isolate; text-align: inherit }}
.toc a {{ color:#1d1d1d; text-decoration:none }} .toc li {{ list-style:none; margin: 5px 0; font-family:'Noto Sans'; font-size: 11pt }}
.toc a::after {{ content: leader('.') target-counter(attr(href), page); }}
.arpage {{ direction: rtl; text-align: right; font-family:'Noto Naskh Arabic', serif; font-size: 11.5pt; line-height: 1.9 }}
.arpage h2 {{ font-family:'Noto Naskh Arabic', serif; text-align:right }}
.arpage li {{ margin: 3px 0 }} .arpage ul {{ margin-right: 18px; margin-left:0 }}
dl {{ margin: 4px 0 }} dt {{ font-family:'Noto Sans'; font-weight:600; color:#0b4d34; margin-top:6px }} dd {{ margin: 1px 0 4px 0 }}
.small {{ font-size: 8.3pt }}
table {{ width:100%; border-collapse: collapse; margin: 6px 0 10px; font-size: 9pt }}
th {{ background:#0b4d34; color:white; font-family:'Noto Sans'; font-weight:600; text-align:left; padding:4px 5px }}
td {{ border-bottom: 1px solid #ddd; padding: 4px 5px; vertical-align: top }}
tr {{ page-break-inside: avoid }}
td.num {{ text-align:right; white-space:nowrap; font-family:'Noto Sans' }}
td.code, code {{ font-family: 'DejaVu Sans Mono', monospace; font-size: 8pt }}
.section {{ page-break-before: always }}
.cover {{ page: cover; box-sizing: border-box; height: 296mm; background: #0b4d34; color: white; position: relative; padding: 40mm 22mm 0 }}
.cover h1 {{ color:white; font-size: 34pt; margin:0 }}
.cover .sub {{ font-family:'Noto Sans'; font-size: 15pt; margin-top: 6mm; color:#e9f2ee }}
.cover .ar {{ text-align:left; direction: rtl; font-size: 20pt; margin-top: 12mm; color:#fff }}
.cover .band {{ height: 4mm; background:#c1272d; width: 60mm; margin: 12mm 0 }}
.cover .meta {{ position:absolute; bottom: 30mm; left: 22mm; font-family:'Noto Sans'; font-size: 10pt; line-height:1.7; color:#dfe9e4 }}
.kpis {{ display: flex; gap: 6px; margin: 8px 0 12px }}
.kpi {{ flex:1; border:1px solid #cfe0d8; border-top: 4px solid #0b4d34; padding: 6px 8px; background:#f6faf8 }}
.kpi b {{ display:block; font-family:'Noto Sans'; font-size: 17pt; color:#0b4d34 }}
.kpi span {{ font-size: 8pt; color:#444 }}
.box {{ border-left: 4px solid #c1272d; background:#fbf3f3; padding: 6px 10px; margin: 8px 0 }}
.box.green {{ border-left-color:#0b4d34; background:#f2f8f5 }}
.quote {{ border:1px solid #ccc; background:#fafafa; padding: 8px 10px; font-size: 11pt; margin: 6px 0 }}
.term {{ font-family:'DejaVu Sans Mono', monospace; font-size: 8pt; background:#1e1e1e; color:#e6e6e6; padding: 8px 10px; white-space: pre-wrap }}
.term.ar {{ font-family:'Noto Naskh Arabic', serif; font-size: 10.5pt; line-height:1.7; white-space: normal; direction: rtl; text-align: right }}
ul {{ margin: 4px 0 8px 16px; padding:0 }} li {{ margin: 2px 0 }}
.sheet td {{ font-size: 8pt; padding: 3px 4px }} .sheet td:nth-child(5), .sheet td:nth-child(6) {{ width: 13mm }}
</style></head><body>

<div class="cover">
  <h1>moroccan-law</h1>
  <div class="sub">Le droit marocain pour Claude et toute intelligence artificielle,<br>construit à partir des textes officiels</div>
  <div class="ar">القانون المغربي لأي ذكاء اصطناعي، انطلاقا من النصوص الرسمية</div>
  <div class="band"></div>
  <div class="sub" style="font-size:12pt">Document de présentation destiné aux experts juridiques<br>(avocats, magistrats, notaires, universitaires) pour relecture et évaluation</div>
  <div class="meta">{tot_t} textes officiels · {FR(tot_a)} articles · 17 domaines<br>
  Source : portail Adala du ministère de la Justice<br>
  Projet open source : github.com/Med-kr/moroccan-law<br>Version du {today}</div>
</div>

<div class="section">
<h2>Sommaire</h2>
<ul class="toc">
<li><a href="#s1">1. En bref</a></li>
<li><a href="#sar">ملخص بالعربية</a></li>
<li><a href="#s2">2. Comment cela fonctionne — un exemple réel</a></li>
<li><a href="#s3">3. Contenu : 17 domaines</a></li>
<li><a href="#s4">4. Fiabilité du texte</a></li>
<li><a href="#s5">5. Mesures</a></li>
<li><a href="#s6">6. Outils pour la pratique</a></li>
<li><a href="#s7">7. Confidentialité et secret professionnel</a></li>
<li><a href="#s8">8. Limites</a></li>
<li><a href="#s9">9. Comment l'essayer</a></li>
<li><a href="#s10">10. Ce que nous demandons aux experts</a></li>
<li><a href="#s11">Glossaire</a></li>
<li><a href="#annA">Annexe A — Textes relus et date de leur version</a></li>
<li><a href="#annB">Annexe B — Grille d'évaluation (60 questions)</a></li>
</ul>
<div class="box green" style="margin-top:14mm"><b>À qui s'adresse ce document ?</b> Aux avocats, magistrats, notaires, adoul, juristes d'entreprise et universitaires invités à évaluer l'outil. Aucune connaissance technique n'est nécessaire : les termes techniques sont expliqués dans le glossaire.</div>
</div>

<div class="section" id="s1">
<h2>1. En bref</h2>
<p><b>moroccan-law</b> met à la disposition d'un assistant d'intelligence artificielle (Claude, ChatGPT, Gemini, Copilot…) le <b>texte officiel</b> du droit marocain, article par article. Lorsqu'un avocat pose une question — en arabe, en français ou en darija —, l'assistant <b>ouvre le texte</b>, cite l'article mot pour mot avec son numéro, la date de la version consolidée et le lien vers le PDF officiel. Il lui est interdit de répondre de mémoire.</p>
<div class="kpis">
 <div class="kpi"><b>{tot_t}</b><span>textes officiels consultables article par article</span></div>
 <div class="kpi"><b>{FR(tot_a)}</b><span>articles</span></div>
 <div class="kpi"><b>95 %</b><span>réponses exactes (chiffre + article) avec l'outil, contre 7 % sans</span></div>
 <div class="kpi"><b>7 150</b><span>documents officiels au catalogue (lois, décrets, circulaires)</span></div>
</div>
<h3>Le problème</h3>
<p>Les assistants d'IA « connaissent » le droit marocain de façon approximative : numéros d'articles inventés, délais erronés, versions abrogées. Sur notre test, sans l'outil, le modèle ne donne le bon chiffre et le bon article que dans <b>7 %</b> des cas. Pour un praticien, une telle réponse est inutilisable.</p>
<h3>La solution</h3>
<ul>
<li>Les textes sont extraits des <b>PDF officiels</b> du portail Adala (ministère de la Justice), avec leur date de consolidation et leur lien source.</li>
<li>Des <b>outils de recherche</b> permettent à l'assistant de trouver l'article pertinent, de le lire, de suivre les renvois et les notes de modification.</li>
<li>Des <b>règles de réponse</b> obligent l'assistant à citer, dater, distinguer le texte de l'interprétation et signaler ses limites.</li>
<li>Des outils pratiques : <b>calcul des délais</b> de procédure civile, <b>dispositions transitoires</b>, comparaison ancien/nouveau code de procédure civile, modèles de requêtes.</li>
</ul>
<div class="box green"><b>Ce que nous demandons aux experts :</b> relire les réponses de l'assistant sur des questions réelles et noter leur exactitude juridique (grille en annexe B). Votre avis est la seule mesure que nos contrôles automatiques ne peuvent pas remplacer.</div>
</div>

<div class="section arpage" id="sar" dir="rtl">
<h2>ملخص بالعربية</h2>
<p><b>moroccan-law</b> أداة مفتوحة المصدر تضع رهن إشارة مساعدات الذكاء الاصطناعي (Claude وChatGPT وGemini وغيرها) <b>النص الرسمي</b> للقانون المغربي مادة بمادة، انطلاقا من ملفات PDF المنشورة في بوابة عدالة لوزارة العدل. حين يطرح المحامي سؤاله بالعربية أو الفرنسية أو الدارجة، يفتح المساعد النص الرسمي ويستشهد بالمادة حرفيا مع رقمها وتاريخ الصيغة المحينة ورابط المصدر، ويُمنع عليه الجواب من الذاكرة.</p>
<ul>
<li><b>{tot_t} نصا رسميا و{FR(tot_a)} مادة</b>: 95 نصا روجعت نصا نصا في 16 مجالا (المدني، المسطرة المدنية، الجنائي، الأسرة، الشغل، التجاري، العقاري، الإداري…)، و718 قانونا آخر مستخرجة آليا مع مراقبة آلية للجودة.</li>
<li><b>الدقة</b>: 99.88% من الكلمات مطابقة لمستخرجين آخرين مستقلين، وكل ملاحظة روجعت، وصُححت أخطاء موجودة في ملفات PDF الرسمية نفسها مع توثيق السبب.</li>
<li><b>القياس</b>: مع الأداة يجد المساعد الرقم والمادة الصحيحين في 95% من الحالات، مقابل 7% بدونها.</li>
<li><b>أدوات عملية</b>: حساب الآجال وفق المادة 602 من القانون 58.25، الأحكام الانتقالية، مقارنة المسطرة المدنية القديمة والجديدة، نماذج مقالات.</li>
<li><b>الحدود</b>: لا يتضمن الاجتهاد القضائي (بوابة المجلس الأعلى للسلطة القضائية محمية برمز تأكيد)، ولا المدونة العامة للضرائب، والنص محين إلى تاريخ الصيغة المنشورة فقط. هي أداة مساعدة للمهني، لا استشارة قانونية.</li>
</ul>
<div class="box green"><b>ما نطلبه من الخبراء</b>: طرح أسئلة حقيقية على المساعد وتقييم أجوبته (الشبكة في الملحق ب). كل جواب خاطئ يتحول إلى اختبار آلي حتى لا يتكرر الخطأ.</div>
</div>

<div class="section" id="s2">
<h2>2. Comment cela fonctionne — un exemple réel</h2>
<p><b>Question d'un avocat, en darija :</b> « ch7al mn youm 3ndi bach nsta2nef 7okm ibtida2i ? » (combien de jours pour faire appel d'un jugement de première instance ?)</p>
<h3>Étape 1 — l'assistant cherche dans le texte officiel, puis lit l'article</h3>
<div class="quote ar"><b>المادة 204 — القانون رقم 58.25 المتعلق بالمسطرة المدنية</b><br>{"<br>".join(E(x) for x in art_body)}</div>
<p class="small">Source affichée par l'outil : PDF officiel sur adala.justice.gov.ma, date de mise à jour du portail et date d'extraction.</p>
<h3>Étape 2 — il calcule le délai selon l'article 602 (délais francs, jours fériés)</h3>
<div class="term ar">{"<br>".join(E(x) for x in del_lines)}</div>
<h3>Étape 3 — il répond, dans la langue de la question</h3>
<p>Il cite l'article 204 (30 jours à compter de la notification) et l'article 602 (délai franc, prorogation au premier jour ouvrable), donne la date limite, recommande d'agir la veille par prudence, signale les jours fériés religieux possibles et, si le jugement est antérieur à la loi 58.25, renvoie à l'article 643 (dispositions transitoires).</p>
<div class="box"><b>Règle n° 1 :</b> jamais de citation de mémoire. Si un article n'existe pas dans la version consolidée, l'outil répond « NOT FOUND » et affiche, le cas échéant, la note de bas de page qui en explique l'abrogation.</div>
</div>

<div class="section" id="s3">
<h2>3. Contenu : 17 domaines</h2>
<p>Les 16 premiers domaines contiennent <b>95 textes relus un par un</b> (77 en arabe, 15 versions françaises, 3 textes abrogés conservés pour comparaison). Le 17e, <code>maroc-corpus</code>, regroupe <b>718 autres lois</b> extraites automatiquement derrière des contrôles de qualité.</p>
<table><tr><th>Domaine (skill)</th><th>Matière</th><th>Principaux textes</th><th>Textes</th><th>Articles</th></tr>
{skills_table}
<tr><td></td><td><b>Total</b></td><td></td><td class="num"><b>{tot_t}</b></td><td class="num"><b>{FR(tot_a)}</b></td></tr></table>
<p class="small">Le domaine <code>maroc-droit</code> donne en outre accès au catalogue complet du portail (7 150 documents : lois, décrets, arrêtés, circulaires du ministère, conventions internationales, décisions de la Cour constitutionnelle), avec téléchargement du PDF officiel.</p>
</div>

<div class="section" id="s4">
<h2>4. Fiabilité du texte : comment elle est contrôlée</h2>
<p>Les textes sont extraits automatiquement de PDF ; ils sont donc contrôlés automatiquement, puis les écarts sont relus.</p>
<table><tr><th>Contrôle</th><th>Résultat (textes relus)</th></tr>
<tr><td>Comparaison mot à mot avec deux autres extracteurs (poppler, MuPDF)</td><td>99,88 % des 943 756 mots arabes et 99,98 % des 317 801 mots français confirmés ; les 301 mots restants relus un par un (mots que les autres extracteurs coupent en deux)</td></tr>
<tr><td>Chiffres (délais, montants, numéros d'articles et de lois)</td><td>66 127 chiffres comparés ; 6 non confirmés, dont 4 numéros de dahir imprimés à l'envers dans le PDF officiel et remis dans l'ordre</td></tr>
<tr><td>Polices défectueuses des PDF (lettres fausses identiques pour tous les extracteurs)</td><td>chaque police comparée aux mêmes polices des autres fichiers ; 20 glyphes corrigés dans 15 textes</td></tr>
<tr><td>Notes laissées par l'analyseur (lacunes de numérotation, articles vides)</td><td>105 notes, toutes expliquées : 75 abrogations justifiées par une note du texte, 22 citations dans des lois modificatives, 8 relues à la main</td></tr>
<tr><td>Modifications législatives</td><td>chaque loi modificative connue du portail est bien citée dans le texte consolidé (0 manquante)</td></tr>
<tr><td>Notes de bas de page</td><td>3 979 (arabe) et 1 202 (français), rattachées à leur article</td></tr></table>
<h3>Erreurs trouvées dans les PDF officiels eux-mêmes</h3>
<ul>
<li>Loi 17-95 (sociétés anonymes), version française : intitulés des articles 353 et 353 bis <b>inversés</b> (corrigé par un erratum documenté, prouvé par les notes et la version arabe).</li>
<li>Loi 25-90 (lotissements) : le texte de l'article 74 bis <b>n'est pas imprimé</b> dans la version consolidée (vérifié sur l'image de la page) ; un avertissement s'affiche sous l'article.</li>
<li>Code du travail, article 256 : en vigueur dans la version arabe, indiqué abrogé dans la version française ; la divergence s'affiche sous l'article.</li>
<li>36 numéros de dahir ou de décret imprimés à l'envers (« 11.03.1 » pour 1.11.03), remis dans l'ordre ; trente-huit espaces manquants après <bdi class="ar">أو</bdi>.</li>
</ul>
<h3>Le corpus étendu (718 lois)</h3>
<p>Même extraction, mêmes outils, mais pas de relecture texte par texte. Des contrôles automatiques écartent tout texte douteux : sur 824 lois, <b>106 ont été écartées</b> avec leur motif (aucun article reconnu, structure non reconnue, chiffres altérés par la police — repérés par des dates impossibles comme « 62 septembre » —, tableaux de montants fusionnés). Comparaison mot à mot : 99,76 % de 1,5 million de mots confirmés. L'assistant doit signaler qu'un texte provient de ce corpus.</p>
<div class="box"><b>Ce n'est pas un certificat.</b> Aucun contrôle automatique ne prouve que 2,7 millions de mots sont tous exacts. Avant tout usage contentieux, la citation doit être vérifiée sur le PDF officiel (lien fourni à chaque réponse) ou au Bulletin officiel.</div>
</div>

<div class="section" id="s5">
<h2>5. Mesures</h2>
<h3>Trouver et citer la bonne disposition (100 questions, Claude Sonnet 5.5, mesuré le 19/11/2026)</h3>
<table><tr><th></th><th>Avec l'outil</th><th>Sans</th></tr>
<tr><td>Chiffre <b>et</b> numéro d'article exacts</td><td class="num"><b>95 %</b></td><td class="num">7 %</td></tr>
<tr><td>Chiffre exact</td><td class="num">100 %</td><td class="num">48 %</td></tr>
<tr><td>Numéro d'article exact</td><td class="num">95 %</td><td class="num">9 %</td></tr></table>
<p class="small">Questions « à trou » générées à partir des textes (un chiffre retiré d'une phrase). Mesure la capacité à trouver la disposition, pas le raisonnement juridique. Mesure faite sur la version d'alors (79 textes), avant les dernières corrections ; non refaite depuis (coût), les textes interrogés étant inchangés pour 97 questions sur 100.</p>
<h3>Questions de praticien (darija, français, arabe ; 16 domaines)</h3>
<table><tr><th>Jeu</th><th>Réponse attendue présente dans l'article</th><th>Article trouvé dans les 5 premiers résultats</th><th>… en premier</th></tr>
<tr><td>40 questions (ayant servi à améliorer la recherche)</td><td class="num">40 / 40</td><td class="num">40 / 40</td><td class="num">34 / 40</td></tr>
<tr><td>20 questions nouvelles, jamais utilisées pour le réglage</td><td class="num">20 / 20</td><td class="num">17 / 20</td><td class="num">13 / 20</td></tr></table>
<div class="box green"><b>Un résultat instructif :</b> ces questions ont été rédigées avec l'aide d'une IA (Claude). Sept réponses qu'elle avait écrites « de mémoire » se sont révélées fausses une fois confrontées au texte — par exemple, la garde ne prend pas fin à 15 ans (elle dure jusqu'à la majorité légale, 15 ans étant l'âge du choix, art. 166 du Code de la famille) ; le délai d'opposition est de 15 jours (art. 200 de la loi 58.25) ; la déclaration d'un accident du travail se fait dans les cinq jours (art. 15 de la loi 18.12). C'est la raison d'être de la règle « jamais de mémoire ».</div>
</div>

<div class="section" id="s6">
<h2>6. Outils pour la pratique</h2>
<table><tr><th>Outil</th><th>Ce qu'il fait</th></tr>
<tr><td>Recherche</td><td>Classement par pertinence ; insensible aux hamzas, voyelles, article et prépositions attachés ; cherche aussi dans les intitulés ; synonymes doctrinaux vérifiés dans les textes (par exemple <bdi class="ar">الشرط الجزائي</bdi> → <bdi class="ar">التعويض المتفق عليه</bdi>, DOC art. 264).</td></tr>
<tr><td>Lecture d'articles</td><td>Plages (43..47), articles bis/ter (353 bis = <bdi class="ar">353 المكررة</bdi>), sous-articles (65-1) ; notes de modification ; notes d'abrogation quand l'article n'existe plus.</td></tr>
<tr><td>Dispositions transitoires</td><td>Affiche les dispositions transitoires et finales d'un texte (ex. art. 643 de la loi 58.25 : les délais commencés avant l'entrée en vigueur restent régis par l'ancienne loi ; les nouvelles voies de recours ne s'appliquent pas aux jugements antérieurs).</td></tr>
<tr><td>Calcul des délais</td><td>Article 602 de la loi 58.25 (délai franc, prorogation), jours fériés du décret 2.77.169, panne de la plateforme électronique (art. 639), nouveau départ du délai (art. 212 et 380) ; alerte sur les fêtes religieuses (date fixée par l'observation du croissant).</td></tr>
<tr><td>Comparaison</td><td>Rapproche un article du code de procédure civile de 1974 de l'article le plus proche de la loi 58.25 (similarité textuelle, pas une table de concordance officielle).</td></tr>
<tr><td>Modèles</td><td>Requête introductive, requête d'appel, mémoire en cassation : chaque mention obligatoire renvoie à son article.</td></tr>
<tr><td>Catalogue</td><td>7 150 documents officiels du portail, recherche par titre ou numéro, téléchargement du PDF.</td></tr></table>
<h3>Accessible depuis toute IA</h3>
<p>Claude Code (plugin), Claude Desktop, ChatGPT, Gemini, Copilot, Cursor, Windsurf, Codex, LM Studio — via un serveur MCP (local ou HTTP) — ou sous forme de jeu de données ouvert (41 410 articles, une ligne par article, avec source et version).</p>
</div>

<div class="section" id="s7">
<h2>7. Confidentialité et secret professionnel</h2>
<p>L'avocat est tenu au secret professionnel (<bdi class="ar">يجب على المحامي … التقيد بالسر المهني</bdi>, art. 46 de la loi 66.23). Il faut donc savoir où vont les informations :</p>
<ul>
<li><b>Les textes et les outils</b> fonctionnent sur l'ordinateur de l'utilisateur : la recherche d'un article ne transmet rien à personne. Le seul accès réseau est le téléchargement d'un PDF officiel depuis adala.justice.gov.ma, à la demande.</li>
<li><b>La question et la réponse</b> passent par le service d'IA choisi par l'utilisateur (Anthropic, OpenAI, Google…), selon les conditions de ce service. moroccan-law n'y ajoute rien et ne collecte aucune donnée.</li>
<li><b>Recommandation :</b> ne pas saisir de noms, numéros de dossier, montants ou faits permettant d'identifier un client ; poser la question en termes généraux ou anonymisés ; vérifier les conditions de conservation des données du service d'IA (ou utiliser un modèle local, par exemple avec LM Studio).</li>
</ul>
</div>

<div class="section" id="s8">
<h2>8. Limites</h2>
<ul>
<li><b>Jurisprudence :</b> seules les décisions de la Cour constitutionnelle (catalogue). Le portail officiel du CSPJ (environ 52 000 arrêts de la Cour de cassation) impose un code de confirmation : il n'est pas aspiré. L'assistant oriente vers le portail et analyse un arrêt que l'utilisateur lui transmet ; il ne cite jamais un arrêt de mémoire.</li>
<li><b>Code général des impôts :</b> absent du portail Adala. Les lois de finances y figurent, mais leurs PDF lisent certaines lettres comme des chiffres : elles sont écartées plutôt que publiées fausses.</li>
<li><b>Décrets et arrêtés d'application :</b> accessibles en PDF via le catalogue, pas encore article par article.</li>
<li><b>Mise à jour :</b> les textes sont à jour à la date de la version consolidée publiée par le ministère, pas au-delà (ex. Code de la famille consolidé au 29 juillet 2021, Code pénal au 22 août 2024). Une vérification hebdomadaire automatique signale les textes remplacés sur le portail.</li>
<li><b>Versions françaises :</b> souvent plus anciennes que les versions arabes (Code du travail : 2011 contre 2026) ; signalées comme telles. Seul l'arabe fait foi.</li>
<li><b>Extraction automatique :</b> tableaux aplatis, quelques espaces parasites possibles.</li>
<li><b>Information juridique, pas une consultation.</b> L'outil assiste le professionnel ; il ne remplace pas son analyse. Pour un justiciable, l'assistant recommande de consulter un avocat.</li>
</ul>
</div>

<div class="section" id="s9">
<h2>9. Comment l'essayer</h2>
<table><tr><th>Avec</th><th>Démarche</th></tr>
<tr><td>Claude Code</td><td>Deux commandes : <code>/plugin marketplace add Med-kr/moroccan-law</code> puis <code>/plugin install moroccan-law@moroccan-law</code>. Poser ensuite la question normalement.</td></tr>
<tr><td>Claude Desktop, Cursor, VS Code, Gemini, LM Studio…</td><td>Télécharger le dépôt (github.com/Med-kr/moroccan-law), puis ajouter le serveur MCP dans les réglages de l'application (une ligne de configuration, décrite dans <code>docs/USE_WITH_ANY_AI.md</code>). Python 3.10 ou plus récent, sans autre logiciel.</td></tr>
<tr><td>ChatGPT et applications en ligne</td><td>Le serveur fonctionne aussi en mode HTTP (adresse web sécurisée et jeton d'accès) ; mise en place à faire par un technicien.</td></tr>
<tr><td>Sans installation</td><td>Démonstration en séance avec l'auteur, sur vos propres questions.</td></tr></table>
<h3>Questions types pour commencer</h3>
<ul><li>« Ch7al mn youm 3ndi bach nsta2nef 7okm ibtida2i ? » (délai d'appel)</li>
<li>« Quelles sont les mentions obligatoires de la requête introductive d'instance ? »</li>
<li>« ما هي شروط إسناد الحضانة للأب بعد زواج الأم؟ »</li>
<li>« Calcule l'indemnité de licenciement d'un salarié ayant 7 ans d'ancienneté. »</li></ul>
</div>

<div class="section" id="s10">
<h2>10. Ce que nous demandons aux experts</h2>
<ol>
<li>Installer l'outil (ou le tester avec nous) et poser à l'assistant les questions de la grille ci-après, ou vos propres questions de pratique.</li>
<li>Noter chaque réponse : <b>A</b> exacte et complète · <b>B</b> exacte, mais incomplète · <b>C</b> trompeuse · <b>D</b> fausse ; et ajouter un commentaire (exception oubliée, texte d'application, jurisprudence contraire, application dans le temps…).</li>
<li>Nous signaler toute erreur de texte (article mal découpé, mot erroné, version dépassée — l'annexe A donne la date de chaque version).</li>
<li>Nous dire quels textes ajouter en priorité (décrets d'application, code général des impôts, textes sectoriels) et quels outils seraient utiles dans votre pratique.</li>
</ol>
<p>Chaque réponse notée C ou D devient un test automatique, pour que l'erreur ne revienne pas. Les retours peuvent être envoyés sur GitHub (issues) ou directement à l'auteur.</p>
<div class="box green"><b>Contact :</b> github.com/Med-kr/moroccan-law — projet open source (licence MIT), indépendant, non affilié au ministère de la Justice, au Secrétariat général du gouvernement ni à Anthropic. La seule source authentique du droit marocain est le Bulletin officiel.</div>
</div>

<div class="section" id="s11">
<h2>Glossaire</h2>
<dl>
<dt>Assistant d'IA</dt><dd>Programme conversationnel (Claude, ChatGPT, Gemini…) qui répond en langage naturel. Seul, il peut se tromper sur les textes ; moroccan-law lui donne accès aux textes officiels.</dd>
<dt>Skill (compétence)</dt><dd>Dossier qui donne à Claude les textes d'un domaine, les outils pour y chercher et les règles de réponse. moroccan-law en contient 17.</dd>
<dt>Plugin</dt><dd>Paquet qui installe les 17 skills d'un coup dans Claude Code.</dd>
<dt>Serveur MCP</dt><dd>« Model Context Protocol » : norme ouverte qui permet à n'importe quel assistant d'IA d'utiliser les mêmes outils (lire un article, chercher, calculer).</dd>
<dt>Version consolidée (صيغة محينة)</dt><dd>Texte de la loi intégrant ses modifications successives, publié par le ministère de la Justice sur Adala, à une date donnée.</dd>
<dt>Corpus étendu</dt><dd>Les 718 lois extraites automatiquement, contrôlées par programme mais non relues texte par texte.</dd>
<dt>Extraction, extracteur</dt><dd>Lecture du texte contenu dans un PDF par un programme ; trois programmes différents sont comparés pour repérer les erreurs.</dd>
<dt>Erratum</dt><dd>Correction documentée d'une erreur imprimée dans le PDF officiel lui-même, avec sa justification.</dd>
<dt>Jeu de données</dt><dd>Fichier contenant les 41 410 articles, une ligne par article, réutilisable par tout outil.</dd>
</dl>
</div>

<div class="section" id="annA">
<h2>Annexe A — Textes relus et date de leur version</h2>
<p class="small">« Version » : date de consolidation imprimée dans le PDF officiel (— si le PDF n'en indique pas). « Adala » : date de mise à jour du fichier sur le portail. Un expert peut ainsi repérer d'un coup d'œil une version dépassée.</p>
<table class="sheet"><thead><tr><th>Domaine</th><th>Texte</th><th>Langue</th><th>Articles</th><th>Version</th><th>Adala</th></tr></thead>
{rev_table}</table>
</div>

<div class="section" id="annB">
<h2>Annexe B — Grille d'évaluation (60 questions)</h2>
<p class="small">Notes : A exacte et complète · B exacte mais incomplète · C trompeuse · D fausse. « Article attendu » : disposition que l'outil doit retrouver (vérifiée dans le texte officiel).</p>
<table class="sheet"><thead><tr><th>#</th><th>Domaine</th><th>Question</th><th>Article attendu</th><th>Note</th><th>Commentaire</th></tr></thead>
{sheet}</table>
<p class="small">Expert : ____________________ &nbsp; Qualité : ____________________ &nbsp; Date : ____________</p>
</div>
</body></html>"""
html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presentation.html")
open(html_path, "w", encoding="utf-8").write(doc)
import weasyprint
weasyprint.HTML(html_path).write_pdf(OUT)
print(OUT)
