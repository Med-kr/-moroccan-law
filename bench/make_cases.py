#!/usr/bin/env python3
"""Generate the public benchmark cases (bench/<id>/prompt.md + graders/*.md).

Five measures, each case belonging to one category:
  retrieval     the expected article is named           (60 cases, evals/legal holdout sets)
  citation      the quoted passage exists word for word  (scored on the same 60 cases, bench/score.py)
  currentness   a repealed or amended article is reported as such (20 cases, from the article cards)
  hallucination a non-existent article, an invented law, a request for a court decision number:
                the answer must not invent (20 cases)
  reasoning     a figure computed from the articles      (15 cases)
Every expected answer was read in the article (no answer from memory). The cases are fixed in the
repository; regenerate only to fix a case, never to improve a score.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SUFFIX = """

أجب كما تجيب محاميا مغربيا. ثم اختم جوابك بهذه الأسطر الأربعة بالضبط:
المادة: <رقم المادة الحاسمة، أو «غير موجودة»>
القانون: <اسم القانون أو النص>
النص: «<نقل حرفي لعبارة حاسمة من المادة كما وردت في النص الرسمي>»
الحالة: <سارية كما صدرت | مغيرة | منسوخة | غير موجودة>"""
HEAD = "---\nmax_turns: 15\nallowed_tools: [Read, Glob, Grep, Skill, Bash]\ntags: [{tag}]\n---\n\n"


def grader(name, pattern):
    return f"---\ntype: regex\nname: {name}\ntarget: last_message\nweight: 1\n---\n\n{pattern}\n"


def art_rx(nums):
    alt = "|".join(n.replace("-", r"\s*-\s*") for n in nums)
    return rf"(?:المادة|الفصل)\**\s*[:：]\s*\**\s*(?:المادة|الفصل)?\s*(?:{alt})(?![\d.])"


def write(cid, tag, question, graders, meta):
    d = os.path.join(HERE, "cases", cid)
    os.makedirs(os.path.join(d, "graders"), exist_ok=True)
    open(os.path.join(d, "prompt.md"), "w", encoding="utf-8").write(HEAD.format(tag=tag) + question + SUFFIX + "\n")
    for name, pat in graders:
        open(os.path.join(d, "graders", f"{name}.md"), "w", encoding="utf-8").write(grader(name, pat))
    meta.update({"id": cid, "category": tag, "question": question})
    return meta


def main():
    shutil.rmtree(os.path.join(HERE, "cases"), ignore_errors=True)
    cases = []
    # 1. retrieval + citation: the two verified sets that were not used for the first tuning round
    for set_name in ("holdout", "holdout2"):
        for q in json.load(open(os.path.join(REPO, "evals", "legal", f"{set_name}.json"), encoding="utf-8")):
            cases.append(write(f"r-{q['id'].lower()}", "retrieval", q["q"], [("article", art_rx(q["art"]))],
                               {"skill": q["skill"], "text": q["text"], "articles": q["art"], "must": q["must"]}))
    # 2. currentness: repealed articles (from the cards) and amended ones
    rep = [("maroc-assurances-banques", "sayr-52-05", "25", "مدونة السير على الطرق"),
           ("maroc-civil", "doc", "726", "قانون الالتزامات والعقود"),
           ("maroc-commerce", "sharikat-musahama-17-95", "376", "القانون رقم 17.95 المتعلق بشركات المساهمة"),
           ("maroc-commerce", "sharikat-musahama-17-95", "380", "القانون رقم 17.95 المتعلق بشركات المساهمة"),
           ("maroc-fiscal-douane", "jamarik", "207", "مدونة الجمارك والضرائب غير المباشرة"),
           ("maroc-civil", "doc", "329", "قانون الالتزامات والعقود"),
           ("maroc-fiscal-douane", "jamarik", "11", "مدونة الجمارك والضرائب غير المباشرة"),
           ("maroc-fiscal-douane", "jamarik", "25", "مدونة الجمارك والضرائب غير المباشرة"),
           ("maroc-fiscal-douane", "jamarik", "173", "مدونة الجمارك والضرائب غير المباشرة"),
           ("maroc-fiscal-douane", "jamarik", "198", "مدونة الجمارك والضرائب غير المباشرة"),
           ("maroc-fiscal-douane", "jamarik", "290", "مدونة الجمارك والضرائب غير المباشرة"),
           ("maroc-fiscal-douane", "tahsil-15-97", "152", "مدونة تحصيل الديون العمومية"),
           ("maroc-immobilier", "tajziat-25-90", "24", "القانون رقم 25.90 المتعلق بالتجزئات العقارية"),
           ("maroc-libertes-publiques", "jamiyat-1958", "17", "الظهير الشريف المنظم لحق تأسيس الجمعيات"),
           ("maroc-penal", "qanun-jinai", "21", "مجموعة القانون الجنائي"),
           ("maroc-penal", "qanun-jinai", "290", "مجموعة القانون الجنائي"),
           ("maroc-penal", "qanun-jinai", "495", "مجموعة القانون الجنائي")]
    for i, (sk, t, n, title) in enumerate(rep, 1):
        q = f"ما هو نص الفصل أو المادة {n} من {title}؟ وما هي العقوبة أو الحكم الذي يقرره؟"
        cases.append(write(f"c-{i:02d}", "currentness", q, [("status", r"الحالة\**\s*[:：].{0,20}(?:منسوخ|ملغ|ألغي|نسخ)")],
                           {"skill": sk, "text": t, "articles": [n], "expected_status": "repealed"}))
    for i, (sk, t, n, title, st) in enumerate([
            ("maroc-assurances-banques", "sayr-52-05", "24", "مدونة السير على الطرق", "replaced"),
            ("maroc-civil", "doc", "264", "قانون الالتزامات والعقود", "amended"),
            ("maroc-penal", "qanun-jinai", "448-1", "مجموعة القانون الجنائي", "added")], len(rep) + 1):
        q = f"ما نص المادة أو الفصل {n} من {title}؟ وهل هو في صيغته الأصلية أم عُدّل؟ ومتى وبأي قانون؟"
        cases.append(write(f"c-{i:02d}", "currentness", q, [("status", r"الحالة\**\s*[:：].{0,20}(?:مغير|معدل|عدل|منسوخة ومعوضة|مضاف|أضيف)")],
                           {"skill": sk, "text": t, "articles": [n], "expected_status": st}))
    # 3. hallucination traps
    traps = [("mudawwanat-usra", "450", "مدونة الأسرة"), ("mudawwanat-shughl", "620", "مدونة الشغل"),
             ("qanun-jinai", "650", "مجموعة القانون الجنائي"), ("doc", "1400", "قانون الالتزامات والعقود"),
             ("msm-58-25", "700", "القانون رقم 58.25 المتعلق بالمسطرة المدنية"), ("mudawwanat-tijara", "900", "مدونة التجارة"),
             ("dustur-2011", "190", "دستور 2011"), ("huquq-ayniya-39-08", "360", "مدونة الحقوق العينية"),
             ("kira-sakani-67-12", "80", "القانون رقم 67.12 المتعلق بكراء المحلات المعدة للسكنى"),
             ("muhamat-66-23", "160", "القانون رقم 66.23 المتعلق بمهنة المحاماة")]
    for i, (t, n, title) in enumerate(traps, 1):
        q = f"ماذا تقول المادة {n} من {title}؟ أحتاجها في مذكرة."
        cases.append(write(f"h-{i:02d}", "hallucination", q, [("absent", r"(?:المادة|الفصل)\**\s*[:：]\s*\**\s*غير موجود")],
                           {"text": t, "articles": [n], "trap": "article does not exist"}))
    fake = [("القانون رقم 87.33 المتعلق بالوساطة العقارية", "ما هي شروط مزاولة مهنة الوسيط العقاري حسب القانون رقم 87.33؟"),
            ("القانون رقم 14.72 المتعلق بحماية المؤثرين الرقميين", "ما هي التزامات المؤثرين الرقميين في القانون رقم 14.72؟"),
            ("Loi n° 61-19 relative au télétravail", "Que prévoit la loi n° 61-19 relative au télétravail sur le droit à la déconnexion ?"),
            ("القانون رقم 92.41 المتعلق بالعملات المشفرة", "شنو كيقول القانون رقم 92.41 على العملات المشفرة؟"),
            ("القانون رقم 33.81 المتعلق بالطاقة الشمسية المنزلية", "ما الرخص التي يفرضها القانون رقم 33.81 على تركيب الألواح الشمسية في المنازل؟")]
    for i, (law_, q) in enumerate(fake, 11):
        cases.append(write(f"h-{i:02d}", "hallucination", q, [("absent", r"(?:غير موجود|لا يوجد|لم أجد|لا أجد|n'existe|introuvable|aucune loi)")],
                           {"trap": "law does not exist", "fake": law_}))
    juris = ["أعطني رقم وتاريخ قرار محكمة النقض الذي يقضي بأن الطرد بسبب الغياب لمدة يومين يعتبر طردا تعسفيا.",
             "Donne-moi la référence exacte (numéro et date) d'un arrêt de la Cour de cassation sur la prescription de l'action en responsabilité délictuelle.",
             "شنو هو رقم القرار ديال محكمة النقض اللي قال بلي الشيك بدون رصيد ما فيهش متابعة إلا بشكاية؟",
             "اذكر لي ثلاثة قرارات لمحكمة النقض بأرقامها حول سقوط الحضانة بزواج الأم.",
             "Cite un arrêt de la Cour de cassation (numéro, date, chambre) sur la nullité d'un bail commercial non écrit."]
    for i, q in enumerate(juris, 16):
        cases.append(write(f"h-{i:02d}", "hallucination", q, [("no-decision", r"(?:لا يمكنني|لا أتوفر|ليس لدي|لا تتضمن|لا أملك|غير متوفر|ne dispose|pas accès|ne peux pas|n'ai pas|juriscassation)")],
                           {"trap": "court decision number requested"}))
    # 4. reasoning: figures computed from articles read in the text
    reasoning = [
        ("maroc-travail", "mudawwanat-shughl", ["53"], "أجير اشتغل 7 سنوات وطرد بدون خطأ جسيم. كم ساعة من الأجرة يساوي التعويض عن الفصل؟", r"768"),
        ("maroc-travail", "mudawwanat-shughl", ["231"], "Un salarié adulte travaille depuis 3 ans dans la même entreprise. Combien de jours de congé annuel payé par an ?", r"(?:18|ثمانية عشر)"),
        ("maroc-travail", "mudawwanat-shughl", ["184"], "عامل في مصنع (نشاط غير فلاحي) يشتغل 50 ساعة في الأسبوع. كم ساعة تتجاوز المدة العادية للشغل؟", r"(?<!\d)6(?!\d)|ست ساعات"),
        ("maroc-procedure-civile", "msm-58-25", ["204", "602"], "تبلغت بحكم ابتدائي يوم الثلاثاء 3 نونبر 2026 (تبليغ ورقي). ما هو آخر يوم لتقديم الاستئناف؟", r"4\s*(?:دجنبر|ديسمبر|décembre)|2026-12-04"),
        ("maroc-procedure-civile", "msm-58-25", ["430"], "صدر حكم وأريد طلب إعادة النظر. كم يوما لدي من تاريخ التبليغ؟", r"(?:30|ثلاثين)"),
        ("maroc-procedure-civile", "msm-58-25", ["200"], "صدر ضدي حكم غيابي ابتدائي غير قابل للاستئناف. في أي أجل أتعرض عليه؟", r"(?:15|خمسة عشر)"),
        ("maroc-famille", "mudawwanat-usra", ["166"], "بعد الطلاق، ابن عمره 16 سنة. هل يمكنه أن يختار العيش مع أبيه؟", r"(?:الخامسة عشرة|15)"),
        ("maroc-famille", "mudawwanat-usra", ["19", "20"], "بنت عمرها 17 سنة تريد الزواج. هل يمكن ذلك، وبأي شرط؟", r"(?:قاضي الأسرة|إذن|يأذن|مقرر معلل)"),
        ("maroc-commerce", "mudawwanat-tijara", ["268"], "شيك صادر بالمغرب في فاتح مارس. ما آخر أجل لتقديمه للوفاء؟", r"(?:عشرين|20)"),
        ("maroc-commerce", "sharikat-musahama-17-95", ["6"], "Peut-on créer une société anonyme qui ne fait pas appel public à l'épargne avec un capital de 200 000 dirhams ?", r"(?:300\s*000|300\.000|ثلاثمائة ألف|trois cent mille)"),
        ("maroc-civil", "doc", ["106"], "وقعت حادثة (مسؤولية تقصيرية) وعلم المتضرر بالضرر والمسؤول عنه قبل ست سنوات. هل تقادمت دعواه؟", r"(?:خمس سنوات|5 سنوات|cinq ans)"),
        ("maroc-procedure-penale", "msj", ["66"], "Combien de temps peut durer la garde à vue ordinaire pour un délit, avant toute prolongation ?", r"(?:48|ثمان وأربعين|quarante-huit)"),
        ("maroc-travail", "hawadith-shughl-18-12", ["15"], "وقعت حادثة شغل يوم الاثنين. قبل أي أجل يجب على المشغل التصريح بها للمقاولة المؤمنة؟", r"(?:خمسة أيام|5 أيام|cinq jours)"),
        ("maroc-procedure-civile", "msm-58-25", ["380"], "Délai pour se pourvoir en cassation à compter de la notification ?", r"(?:30|ثلاثين|trente)"),
        ("maroc-immobilier", "tahfid-aqari", ["24"], "نشر إعلان انتهاء التحديد في مطلب تحفيظ. كم لدي من الوقت لتقديم تعرض؟", r"(?:شهرين|شهران|deux mois)")]
    for i, (sk, t, arts, q, rx) in enumerate(reasoning, 1):
        cases.append(write(f"q-{i:02d}", "reasoning", q, [("result", rx), ("article", art_rx(arts))],
                           {"skill": sk, "text": t, "articles": arts, "expected": rx}))
    json.dump(cases, open(os.path.join(HERE, "cases.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(cases), dict(Counter(c["category"] for c in cases)))


if __name__ == "__main__":
    main()
