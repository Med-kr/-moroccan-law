#!/usr/bin/env python3
"""Review of every note the parser leaves in meta.json ("anomalies").

Each note is classified: explained by a repeal footnote of the text, an article of another
law quoted by an amending law, or reviewed by hand (MANUAL below, with the reason).
Writes data/anomalies-reviewed.json; exit 1 if a note is neither explained nor reviewed,
so that a new one is looked at before release. The extended corpus (maroc-corpus, automatic
extraction behind quality gates, not reviewed text by text) is left out on purpose.
"""
import json,glob,re,os,sys

MANUAL = {
    ("sharikat-musahama-17-95", "numbering gap: 424 -> 441"): "section 15 (articles 425-440) printed as « نسخ. » under its title: repealed",
    ("sharikat-musahama-fr", "numbering gap: 424 -> 441"): "same repealed section as the Arabic version",
    ("sharikat-musahama-fr", "article 376 has no text"): "empty in the Arabic version too, which carries the repeal footnote",
    ("jinsiya", "heading-like line kept as text: 'الفصل الثاني عشر:'"): "cross-reference at the end of a sentence (« ...في الفصل الثاني عشر: »), rightly kept as text",
    ("onf-nisa-103-13", "heading-like line kept as text: 'المادة 7. -"): "article 7 of the criminal procedure code quoted by the amending law, rightly kept as text",
    ("msm-1974-mansukh", "numbering gap: 305 -> 328"): "chapter on arbitration repealed by law 95.17 (footnote 138)",
    ("tajziat-25-90", "article 74 المكررة has no text"): "SOURCE OMISSION: the consolidated PDF prints the heading and note 64 (added by law 34.21) but not the text; checked on the page image; a warning is shown under the article",
    ("mudawwanat-shughl-fr", "article 256 has no text"): "SOURCE DISCREPANCY: abrogated in the French version (law 48-06, footnote 35) but still printed in the Arabic version; the Arabic text prevails, flag it when article 256 is used",
}
QUOTED = re.compile(r"heading-like line kept as text: 'المادة 647-")
REP=re.compile(r"(ألغي|إلغاء|الغاء|نسخ|منسوخ|حذف|abrog|supprim|remplac|transf|نقل|عوض)",re.I)
out={"explained":0,"unexplained":[]}
rows=[]
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for m in sorted(x for x in glob.glob('skills/*/references/*/meta.json') if '/maroc-corpus/' not in x):
    d=json.load(open(m)); slug=m.split('/')[-2]; txt=open(os.path.dirname(m)+'/text.md',encoding='utf-8').read()
    notes=re.findall(r"^\[\^\d+\]:.*(?:\n(?!\[\^|##|#).*)*",txt,re.M)
    for a in d.get('anomalies') or []:
        nums=[]
        g=re.match(r"numbering gap: (\S+) -> (\S+)",a); e=re.match(r"article (\S+) has no text",a); h=re.match(r"heading-like line kept as text: '(.*)'",a)
        if g:
            lo,hi=g.groups()
            try: nums=[str(i) for i in range(int(re.sub(r'\D.*','',lo))+1,int(re.sub(r'\D.*','',hi)))]
            except: nums=[]
        elif e: nums=[e.group(1)]
        else:
            key=next((v for (sl,pre),v in MANUAL.items() if sl==slug and a.startswith(pre)),None)
            if key: rows.append({"text":slug,"note":a,"status":"reviewed","why":key})
            elif QUOTED.match(a): rows.append({"text":slug,"note":a,"status":"quoted","why":"article of the criminal procedure code quoted by law 43.22, which inserts it there"})
            else: out["unexplained"].append((slug,a))
            continue
        ok=False
        for n in notes:
            if REP.search(n) and any(re.search(rf"(?<![\d.\-]){re.escape(x)}(?![\d])",n) for x in nums[:1]+nums[-1:]):
                ok=True;break
        key=next((v for (sl,pre),v in MANUAL.items() if sl==slug and a.startswith(pre)),None)
        if ok: out["explained"]+=1; rows.append({"text":slug,"note":a,"status":"repeal footnote"})
        elif key: rows.append({"text":slug,"note":a,"status":"reviewed","why":key})
        else: out["unexplained"].append((slug,a))
json.dump(rows,open('data/anomalies-reviewed.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
import collections
print(dict(collections.Counter(r["status"] for r in rows)), "| not reviewed:", len(out["unexplained"]))
for x in out["unexplained"]: print("  NOT REVIEWED", x)
sys.exit(1 if out["unexplained"] else 0)
