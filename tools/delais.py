#!/usr/bin/env python3
"""Procedural time limits under the Moroccan civil procedure law (58.25).
Standard library only.

    delais.py calc --from 2026-11-03 --days 30 [--months N] [--electronic]
                   [--holidays 2027-03-20,2027-03-21] [--weekend sat,sun]
                   [--platform-back YYYY-MM-DD]   (electronic act, platform down on the
                                                   last day: art. 639, the day it came back)
                   [--restart 212:YYYY-MM-DD | 380:YYYY-MM-DD]
                        the limit runs anew: art. 212 (change of capacity during the appeal
                        period, 15 days after the new notification), art. 380 (legal aid
                        before cassation, from the notification of the decision)
        last day on which the act can still be done, computed as article 602 says
    delais.py list [words ...] [--text T] [--max N]
        articles of this skill that set a time limit (with the figures found)

How `calc` counts (article 602 of law 58.25, read it with law.py first):
  * time limits are "full" (كاملة): the day of the notification is not counted,
    nor the last day of the period;
  * if the last day is a holiday the limit runs to the first working day after;
  * for acts done electronically the limit runs without interruption until
    midnight of the last day of the period (--electronic).
Holidays: weekly rest days (--weekend, Saturday and Sunday by default) plus the
fixed-date holidays of decree 2.77.169 as amended. Religious holidays depend on
the sighting of the moon: the program estimates them (tabular Hijri calendar, +/- 1 day)
and WARNS when one may fall at the end of the period, but does not extend the limit on
an estimate. Pass the confirmed dates with --holidays.

The result is an arithmetic aid. Which time limit applies, when it starts,
and whether it is suspended or extended (distance, change of capacity, death of
a party ...) are legal questions: read the articles.
"""
from __future__ import annotations

import calendar
import math
import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import law  # noqa: E402

# decree 2.77.169 (consolidated version of 5 February 2026), article 1: fixed-date holidays
FIXED = {(1, 1): "رأس السنة الميلادية", (1, 11): "ذكرى تقديم عريضة الاستقلال", (1, 14): "رأس السنة الأمازيغية",
         (5, 1): "عيد الشغل", (7, 30): "عيد العرش", (8, 14): "يوم وادي الذهب", (8, 20): "ذكرى ثورة الملك والشعب",
         (8, 21): "عيد ميلاد صاحب الجلالة", (10, 31): "عيد الوحدة", (11, 6): "عيد المسيرة الخضراء",
         (11, 18): "عيد الاستقلال"}
LUNAR = "رأس السنة الهجرية (فاتح محرم)، المولد النبوي (12 و13 ربيع الأول)، عيد الفطر (1 و2 شوال)، عيد الأضحى (10 و11 ذي الحجة)"
DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
DAY_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
UNIT = r"(يوما|يوم|أيام|شهرا|شهر|أشهر|شهور|شهرين|سنة|سنوات|سنتين|ساعة)"
LIMIT = re.compile(rf"(?:أجل|آجال|مدة|خلال|داخل|ظرف)[^.؛\n]{{0,60}}?(\(\d+\)|\d+)\s*{UNIT}|"
                   rf"(?:أجل|خلال|داخل|ظرف)\s+(شهر|شهرين|سنة|سنتين)(?:\s|،|\.)")


RELIGIOUS = [((1, 1), "رأس السنة الهجرية"), ((3, 12), "عيد المولد النبوي"), ((3, 13), "عيد المولد النبوي (اليوم الثاني)"),
             ((10, 1), "عيد الفطر"), ((10, 2), "عيد الفطر (اليوم الثاني)"),
             ((12, 10), "عيد الأضحى"), ((12, 11), "عيد الأضحى (اليوم الثاني)")]


def hijri_to_date(y: int, m: int, d: int) -> dt.date:
    """Arithmetical (tabular) Islamic calendar. In Morocco the month starts on the sighting
    of the moon, so the real date can differ by one day (it matched every date announced in
    2024-2025): used only to WARN, never to extend a time limit."""
    jdn = d + math.ceil(29.5 * (m - 1)) + (y - 1) * 354 + (3 + 11 * y) // 30 + 1948440 - 1
    return dt.date.fromordinal(jdn - 1721425)


def religious_estimates(year: int) -> dict[dt.date, str]:
    out = {}
    hy = int((year - 622) * 33 / 32)
    for y in range(hy - 1, hy + 3):
        for (m, d), name in RELIGIOUS:
            g = hijri_to_date(y, m, d)
            if abs(g.year - year) <= 1:
                out[g] = f"{name} {d}/{m}/{y} هـ"
    return out


def religious_near(d: dt.date) -> list[str]:
    """Estimated religious holidays within one day of d."""
    est = religious_estimates(d.year)
    return [f"{name} (تقديريا {fmt(g)})" for g, name in sorted(est.items()) if abs((g - d).days) <= 1]


def add_months(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def why_closed(d: dt.date, weekend: set[int], extra: set[dt.date]) -> str | None:
    if d in extra:
        return "عطلة مدلى بها (--holidays)"
    if (d.month, d.day) in FIXED:
        return FIXED[(d.month, d.day)]
    if d.weekday() in weekend:
        return "عطلة نهاية الأسبوع"
    return None


MONTH_AR = ["يناير", "فبراير", "مارس", "أبريل", "ماي", "يونيو", "يوليوز", "غشت", "شتنبر", "أكتوبر", "نونبر", "دجنبر"]


def fmt(d: dt.date) -> str:
    # the month is spelled out: an all-digit date is displayed reversed inside right-to-left text
    return f"{DAY_AR[d.weekday()]} {d.day} {MONTH_AR[d.month - 1]} {d.year}"


def cmd_calc(o: dict) -> None:
    try:
        start = dt.date.fromisoformat(o["--from"])
        days, months = int(o["--days"] or 0), int(o["--months"] or 0)
        extra = {dt.date.fromisoformat(x) for x in (o["--holidays"] or "").split(",") if x.strip()}
        weekend = {DAYS[x.strip().lower()[:3]] for x in (o["--weekend"] or "sat,sun").split(",") if x.strip()}
    except (TypeError, ValueError, KeyError) as exc:
        law.die(f"bad argument ({exc}). Dates are YYYY-MM-DD; --weekend takes sat,sun,fri ...", 2)
    if not days and not months:
        law.die("give --days N and/or --months N", 2)
    if o["--restart"]:
        # the time limit starts running anew (articles 212 and 380 of law 58.25)
        rule, _, when = o["--restart"].partition(":")
        try:
            renotified = dt.date.fromisoformat(when)
        except ValueError:
            law.die("--restart takes 212:YYYY-MM-DD or 380:YYYY-MM-DD", 2)
        if rule == "212":
            print(f"المادة 212: تغير أهلية أحد الأطراف أثناء أجل الاستئناف، فتوقف الأجل. بلغ الحكم من جديد يوم "
                  f"{fmt(renotified)} لمن له الصفة، ولا يبتدئ سريان الأجل من جديد إلا بعد خمسة عشر (15) يوما.")
            start = renotified + dt.timedelta(days=15)
            print(f"  بداية السريان الجديد (لا يحسب): {fmt(start)} — الأجل كاملا من جديد\n")
        elif rule == "380":
            print(f"المادة 380، الفقرة 3: أوقف أجل النقض بإيداع طلب المساعدة القضائية، ويسري من جديد من تاريخ "
                  f"تبليغ مقرر مكتب المساعدة القضائية (للمحامي المعين) أو قرار الرفض (للطالب): {fmt(renotified)}.\n")
            start = renotified
        else:
            law.die("--restart: rule 212 or 380", 2)
    last_of_period = add_months(start, months) + dt.timedelta(days=days)
    length = " و".join(x for x in (f"{months} شهر" if months else "", f"{days} يوما" if days else "") if x)
    print(f"تاريخ التبليغ أو الإجراء (لا يحسب): {fmt(start)}")
    print(f"الأجل: {length}")
    print(f"اليوم الأخير من الأجل: {fmt(last_of_period)}")
    if o["--electronic"]:
        print(f"إجراء بطريقة إلكترونية (المادة 602، الفقرة 3): إلى غاية منتصف ليل {fmt(last_of_period)}")
        result = last_of_period
        reason = why_closed(result, weekend, extra)
        if reason:
            print(f"  تنبيه: {fmt(result)} يوم عطلة ({reason}). الفقرة 3 تنص على احتساب مستمر؛ "
                  "تحقق من أثر الفقرة 2 على حالتك.")
        if o["--platform-back"]:
            try:
                back = dt.date.fromisoformat(o["--platform-back"])
            except ValueError:
                law.die("--platform-back takes YYYY-MM-DD", 2)
            if back > result:
                print(f"تعذر الولوج إلى المنصة الإلكترونية في اليوم الأخير، واستأنفت عملها يوم {fmt(back)} "
                      "(المادة 639، الفقرة 2، مع بلاغ الإدارة المثبت للعطب):")
                result = back + dt.timedelta(days=1)
                print(f"  يمدد الأجل إلى أول يوم يلي استئناف المنصة: {fmt(result)}")
                print(f"  للاحتياط (قراءة أضيق للنص): القيام بالإجراء يوم استئناف المنصة نفسه، {fmt(back)}.")
    else:
        result = last_of_period + dt.timedelta(days=1)        # full time limit: the last day is not counted
        print(f"الأجل كامل، فلا يحسب اليوم الأخير (المادة 602، الفقرة 1): {fmt(result)}")
        while True:
            reason = why_closed(result, weekend, extra)
            if not reason:
                break
            print(f"  {fmt(result)} يوم عطلة ({reason})، يمتد الأجل (المادة 602، الفقرة 2)")
            result += dt.timedelta(days=1)
    print(f"\n==> آخر يوم يمكن فيه القيام بالإجراء: {fmt(result)}")
    print(f"    للاحتياط: القيام بالإجراء في أجل أقصاه {fmt(last_of_period)}.")
    near = [x for day in sorted({last_of_period, result}) for x in religious_near(day)]
    if near and not extra:
        print("\n!! تنبيه — عيد ديني محتمل قرب نهاية الأجل / fête religieuse possible en fin de délai:")
        for x in dict.fromkeys(near):
            print(f"   - {x}")
        print("   التاريخ الهجري يتحدد برؤية الهلال (فارق يوم ممكن). لم يمدد الأجل آليا: تحقق من بلاغ وزارة الأوقاف "
              "والشؤون الإسلامية ثم أعد الحساب بـ --holidays YYYY-MM-DD.")
    print(f"\n— الأعياد الدينية ({LUNAR}) لا تمدد الأجل آليا لأنها مرتبطة برؤية الهلال؛ "
          "يظهر تنبيه إذا كان أحدها محتملا قرب نهاية الأجل. للاحتساب: --holidays.")
    if not o["--restart"]:
        print("— وقف الأجل وسريانه من جديد: تغير أهلية أحد الأطراف أثناء أجل الاستئناف (المادة 212) أو طلب "
              "المساعدة القضائية قبل النقض (المادة 380): أعد الحساب بـ --restart 212:YYYY-MM-DD أو "
              "--restart 380:YYYY-MM-DD (تاريخ التبليغ الجديد). حالات خاصة أخرى: اقرأ النص.")
    print("— هذا حساب آلي على أساس المادة 602 من القانون رقم 58.25. تحقق من الأجل المطبق ومن بداية سريانه "
          "وحالات الوقف والتمديد في النص.")
    print("— Calcul arithmétique selon l'article 602 de la loi 58-25 ; fêtes religieuses : alerte seulement (date fixée par l'observation du croissant), à ajouter avec --holidays.")


def cmd_list(words: list[str], only: str | None, limit: int) -> None:
    q = [law.norm(w) for w in words]
    shown = 0
    for slug in ([law.resolve(only)] if only else law.texts()):
        rows = []
        for a in law.load_articles(slug):
            if q and not all(w in law.norm(a["body"]) for w in q):
                continue
            found = []
            for m in LIMIT.finditer(a["body"]):
                s = re.sub(r"\s+", " ", m.group(0)).strip(" ،.")
                if s not in found:
                    found.append(s)
            if found:
                rows.append((a, found))
        if not rows:
            continue
        print(f"# {slug} — {len(rows)} مادة تتضمن أجلا")
        for a, found in rows[:limit]:
            print(f"- {a['heading']}: " + " | ".join(found[:4]))
        if len(rows) > limit:
            print(f"  (+{len(rows) - limit} أخرى — استعمل --max أو كلمات للتصفية)")
        shown += len(rows)
        print()
    if not shown:
        law.die("no article with a time limit matches these words.", 3)
    print("— القائمة مستخرجة آليا بالبحث عن صيغ الآجال في النص؛ اقرأ المادة كاملة بـ law.py قبل الاعتماد عليها.")


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    o = {"--from": None, "--days": None, "--months": None, "--holidays": None, "--weekend": None,
         "--electronic": False, "--text": None, "--max": "25", "--platform-back": None, "--restart": None}
    rest = []
    i = 1
    while i < len(argv):
        if argv[i] == "--electronic":
            o[argv[i]] = True
            i += 1
        elif argv[i] in o and i + 1 < len(argv):
            o[argv[i]] = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    if argv[0] == "calc" and o["--from"]:
        cmd_calc(o)
    elif argv[0] == "list":
        cmd_list(rest, o["--text"], int(o["--max"]))
    else:
        law.die(__doc__, 2)


if __name__ == "__main__":
    main(sys.argv[1:])
