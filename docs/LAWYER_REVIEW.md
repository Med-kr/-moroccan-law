# Review sheet for a practising lawyer / ورقة مراجعة لمحام ممارس / Fiche de relecture

Ask Claude each question with the plugin installed, then grade the answer. The expected article
is the one the program checks (`evals/legal/run.py`); the grade is the lawyer's: was the answer
legally right, complete (exceptions, conditions, application in time) and safe to rely on?

Grades: **A** right and complete · **B** right, something missing · **C** misleading · **D** wrong.

| # | Domain | Question | Expected article | Grade | Comment |
|---|---|---|---|---|---|
| T01 | travail | Ch7al howa t-ta3wid 3la l-fasl (indemnité de licenciement) l 5 snin l-oulin? | `mudawwanat-shughl` 53 |  |  |
| T02 | travail | Ch7al mn nhar d l-3otla s-sanawiya l kol chhar? | `mudawwanat-shughl` 231 |  |  |
| T03 | travail | Période d'essai d'un cadre en CDI ? | `mudawwanat-shughl` 14 |  |  |
| T04 | travail | Ch7al mn sa3a d l-khedma f l-3am f l-qita3 ghir l-fila7i? | `mudawwanat-shughl` 184 |  |  |
| T05 | travail | Chno homa l-akhta2 l-jasima li katbarrer l-fasl bla i5tar? | `mudawwanat-shughl` 39 |  |  |
| T06 | travail | Délai de prescription des actions du salarié ? | `mudawwanat-shughl` 395 |  |  |
| F01 | famille | Ch7al howa sinn z-zwaj? | `mudawwanat-usra` 19 |  |  |
| F02 | famille | F ch7al khass l-ma7kama tfsel f d3wat ch-chi9a9? | `mudawwanat-usra` 97 |  |  |
| F03 | famille | Chkoun 3ndo l-7adana l-awwal: l-om wla l-b? | `mudawwanat-usra` 171 |  |  |
| F04 | famille | Imta katsali l-7adana, w imta y9der l-weld ykhtar m3a mn ygles? | `mudawwanat-usra` 166 |  |  |
| F05 | famille | 3iddat l-mra ghir l-7amil? | `mudawwanat-usra` 136 |  |  |
| F06 | famille | Imta kaymna3 t-ta3addod? | `mudawwanat-usra` 40 |  |  |
| C01 | civil | Ch7al t-ta9adom l-3amm f l-iltizamat? | `doc` 387 |  |  |
| C02 | civil | Le contrat tient-il lieu de loi entre les parties ? | `doc` 230 |  |  |
| C03 | civil | Wach l-ma7kama t9der tn99es ch-chart l-jaza2i? | `doc` 264 |  |  |
| C04 | civil | Mas2ouliya 3la l-khata2 (faute) — chmen fasl? | `doc` 78 |  |  |
| P01 | procedure-civile | Ch7al mn youm 3ndi bach nsta2nef 7okm ibtida2i? | `msm-58-25` 204 |  |  |
| P02 | procedure-civile | Délai du pourvoi en cassation ? | `msm-58-25` 380 |  |  |
| P03 | procedure-civile | Kifach kayt7sbo l-ajal (kamla)? | `msm-58-25` 602 |  |  |
| P04 | procedure-civile | 7okm sdar 9bel 58.25: wach kat-tba9 3lih toro9 t-ta3n j-jdida? | `msm-58-25` 643 |  |  |
| P05 | procedure-civile | La plateforme électronique était en panne le dernier jour du délai ? | `msm-58-25` 639 |  |  |
| J01 | penal | 3o9oubat l-9atl l-3amd? | `qanun-jinai` 392 |  |  |
| J02 | penal | 3o9oubat s-sari9a l-3adiya? | `qanun-jinai` 505 |  |  |
| J03 | penal | Imta y9der l-9adi y7kem b 3o9ouba badila? | `qanun-jinai` 35-1 |  |  |
| J04 | procedure-penale | Ch7al mouddat l-7irasa n-nadariya f l-jonah? | `msj` 66 |  |  |
| K01 | commerce | Chèque sans provision : quelle peine ? | `mudawwanat-tijara` 316 |  |  |
| K02 | commerce | Chno howa l-asl t-tijari? | `mudawwanat-tijara` 79 |  |  |
| K03 | commerce | Ch7al 3nd l-mostahlik bach yrj3 f chra mn l-internet? | `himayat-mustahlik-31-08` 36 |  |  |
| I01 | immobilier | Wach r-rasm l-3a9ari n-niha2i y9bel t-ta3n? | `tahfid-aqari` 62 |  |  |
| I02 | immobilier | Quelle est la valeur des inscriptions au titre foncier ? | `huquq-ayniya-39-08` 2 |  |  |
| A01 | administratif | Wach l-idara mlzouma t3ellel l-9rarat s-salbiya? | `taalil-03-01` 1 |  |  |
| N01 | numerique | Traitement de données personnelles : faut-il le consentement ? | `muatayat-09-08` 4 |  |  |
| D01 | droit | Qarinat l-bara2a f d-dostour? | `dustur-2011` 23 |  |  |
| D02 | droit | L-7a99 f mo7akama 3adila? | `dustur-2011` 120 |  |  |
| PI1 | propriete-intellectuelle | Ch7al katb9a 7o9ou9 l-mo2allif mn b3d l-mout? | `huquq-muallif-2-00` 25 |  |  |
| L01 | libertes-publiques | F ch7al khass l-idara tjaweb 3la talab l-ma3louma? | `maalumat-31-13` 16 |  |  |
| B01 | assurances-banques | Prescription des actions dérivant du contrat d'assurance ? | `taminat-17-99` 36 |  |  |
| X01 | fiscal-douane | Ch7al t-ta9adom d d-doyoun l-3omomiya (ta7sil)? | `tahsil-15-97` 123 |  |  |
| W01 | travail | F ch7al khass l-mochaghghil ysrre7 l charikat t-ta2min b 7adithat ch-choghl? | `hawadith-shughl-18-12` 15 |  |  |
| M01 | professions-judiciaires | Wach l-mo7ami mlzoum b s-sir l-mihani? | `muhamat-66-23` 46 |  |  |
| H01 | travail | Ch7al mouddat l-i5tar (préavis) 9bel l-fasl? | `mudawwanat-shughl` 43 |  |  |
| H02 | travail | Ch7al katakhod l-mra d l-3otla d l-wilada? | `mudawwanat-shughl` 152 |  |  |
| H03 | travail | Âge minimum d'embauche ? | `mudawwanat-shughl` 143 |  |  |
| H04 | famille | Imta katwjeb nafa9at z-zawja 3la r-rajel? | `mudawwanat-usra` 194 |  |  |
| H05 | famille | Chno howa l-khol3? | `mudawwanat-usra` 115 |  |  |
| H06 | famille | Ch7al l-7add d l-waṣiya? | `mudawwanat-usra` 277 |  |  |
| H07 | civil | Le dol (التدليس) est-il une cause de rescision ? | `doc` 52 |  |  |
| H08 | civil | Chkoun mas2oul 3la d-darar li kaydir l-7ayawan? | `doc` 86 |  |  |
| H09 | procedure-civile | Ch7al l-ajal d t-ta3arrod 3la 7okm ghiyabi ibtida2i? | `msm-58-25` 200 |  |  |
| H10 | penal | 3o9oubat n-naṣb (escroquerie)? | `qanun-jinai` 540 |  |  |
| H11 | penal | Abus de confiance : quelle peine ? | `qanun-jinai` 547 |  |  |
| H12 | procedure-penale | Wach l-i3ti9al l-i7tiyati tadbir istithna2i? | `msj` 159 |  |  |
| H13 | commerce | Ch7al t-ta9adom d l-kombiyala (lettre de change) 3la l-9abil? | `mudawwanat-tijara` 228 |  |  |
| H14 | commerce | Ch7al l-7add l-a9ṣa d ch-chorraka f SARL? | `sharikat-5-96` 47 |  |  |
| H15 | immobilier | Bach y9der mol d-dar ykhrrej l-mokri (motif sérieux)? | `kira-sakani-67-12` 45 |  |  |
| H16 | immobilier | Ch7al d l-mouda bach l-mokri y9der yktaseb l-7a9 f l-kira t-tijari? | `kira-tijari-49-16` 4 |  |  |
| H17 | droit | Wach l-9anoun howa asma ta3bir 3la irada l-oumma? | `dustur-2011` 6 |  |  |
| H18 | numerique | Wach khass taṣri7 mosba9 l l-CNDP 9bel l-mou3alaja? | `muatayat-09-08` 12 |  |  |
| H19 | travail | Wach t-tasjil f CNSS ilzami l l-mochaghghil? | `daman-ijtimai` 15 |  |  |
| H20 | assurances-banques | Wach l-mo2ammen lih khasso ysrre7 b l-7aditha f ajal mo7added? | `taminat-17-99` 20 |  |  |

Reviewer: ________  Bar: ________  Date: ________

Send the filled sheet as an issue or pull request; every C or D becomes a test.
