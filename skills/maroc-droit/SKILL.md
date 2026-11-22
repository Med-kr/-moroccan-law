---
name: maroc-droit
description: >-
  Droit marocain — point d'entrée général / القانون المغربي: recherche dans le catalogue des
  7150 documents officiels publiés par le ministère de la Justice (portail Adala : lois,
  dahirs, décrets, arrêtés, lois organiques, en arabe et en français ; circulaires du ministère ;
  conventions internationales ; décisions de la Cour constitutionnelle), téléchargement du PDF
  officiel de n'importe lequel, et texte de la Constitution de 2011. À utiliser pour toute
  question de droit marocain qui ne relève pas d'un skill `maroc-*` spécialisé, pour trouver
  un décret ou un arrêté d'application, vérifier si un texte a été modifié ou abrogé, ou
  savoir quel skill consulter. Mots-clés : القانون المغربي، ظهير، مرسوم، قرار، قانون تنظيمي، الدستور، الجريدة الرسمية، عدالة — droit marocain, dahir, décret, arrêté, loi organique, Constitution, Bulletin officiel, Adala, loi marocaine, texte de loi Maroc.
---

# Droit marocain — catalogue général / القانون المغربي

Catalogue construit le 2026-11-19 à partir de <https://adala.justice.gov.ma> :
**7150 documents** (6508 en arabe, 642 en français).

Le catalogue couvre cinq rubriques du portail ; le nom de la rubrique fait partie du chemin
affiché sous chaque résultat et peut servir de mot de recherche :

| Rubrique (mot à chercher) | Contenu |
|---|---|
| `نصوص تشريعية وتنظيمية` | lois, dahirs, décrets, arrêtés |
| `مناشير و دوريات` | circulaires du ministère de la Justice (matière civile, pénale…) |
| `اتفاقيات ومعاهدات` | conventions bilatérales et multilatérales |
| `قرارات المحكمة الدستورية` | décisions de la Cour constitutionnelle |
| `مجلة القضاء والقانون` | revue du ministère (doctrine, commentaires) |

## 1. Choisir le bon skill

Si un skill spécialisé est installé, l'utiliser en priorité : il contient le texte article par
article et un outil de recherche.

| Skill | Domaine |
|---|---|
| `maroc-civil` | Droit civil marocain — القانون المدني المغربي |
| `maroc-procedure-civile` | Procédure civile et organisation judiciaire — المسطرة المدنية والتنظيم القضائي |
| `maroc-penal` | Droit pénal marocain — القانون الجنائي المغربي |
| `maroc-procedure-penale` | Procédure pénale — المسطرة الجنائية |
| `maroc-famille` | Droit de la famille marocain — قانون الأسرة المغربي |
| `maroc-travail` | Droit du travail et protection sociale — قانون الشغل والحماية الاجتماعية |
| `maroc-commerce` | Droit commercial et droit des sociétés — القانون التجاري وقانون الشركات |
| `maroc-immobilier` | Droit immobilier et baux — القانون العقاري والكراء |
| `maroc-professions-judiciaires` | Profession d'avocat et professions judiciaires — مهنة المحاماة والمهن القضائية |
| `maroc-administratif` | Droit administratif et marchés publics — القانون الإداري والصفقات العمومية |
| `maroc-fiscal-douane` | Douanes, recouvrement des créances publiques et fiscalité — الجمارك وتحصيل الديون العمومية والجبايات |
| `maroc-numerique` | Données personnelles, transactions électroniques et cybersécurité — المعطيات الشخصية والمعاملات الإلكترونية والأمن السيبراني |
| `maroc-assurances-banques` | Assurances et banques — التأمينات والأبناك |
| `maroc-propriete-intellectuelle` | Propriété intellectuelle et industrielle — الملكية الفكرية والصناعية |
| `maroc-libertes-publiques` | Libertés publiques et presse — الحريات العامة والصحافة |
| `maroc-corpus` | Autres lois marocaines (extraction automatique) — باقي القوانين المغربية (استخراج آلي) |

## 2. Textes inclus ici

| text | النص | Texte | حجم | صيغة محينة بتاريخ | source |
|---|---|---|---|---|---|
| `dustur-2011` | دستور المملكة المغربية لسنة 2011 | Constitution du Royaume du Maroc (2011) | 180 الفصل | — | 2025-12-25 |
| `dustur-2011-fr` | [نسخة فرنسية — قد لا تكون محينة] دستور المملكة المغربية لسنة 2011 | [Version française — peut ne pas être à jour] Constitution du Royaume du Maroc (2011) | 180 Article | — | 2024-10-09 |

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" article dustur 1 6 117..120
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" search المحاكمة العادلة
```

## 3. Tout autre texte : le catalogue

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/catalog.py" search حماية المعطيات الشخصية
python3 "${CLAUDE_SKILL_DIR}/scripts/catalog.py" search 09.08 --lang ar
python3 "${CLAUDE_SKILL_DIR}/scripts/catalog.py" search "protection du consommateur" --lang fr
python3 "${CLAUDE_SKILL_DIR}/scripts/catalog.py" search مرسوم مدونة الشغل --max 40
python3 "${CLAUDE_SKILL_DIR}/scripts/catalog.py" show <id>
python3 "${CLAUDE_SKILL_DIR}/scripts/catalog.py" get <id>      # télécharge le PDF officiel
```

Si `${CLAUDE_SKILL_DIR}` n'est pas développé, utiliser le « Base directory for this skill ».

`get` enregistre le PDF dans `~/.cache/moroccan-law-skills/` et affiche son chemin : le lire
ensuite avec l'outil de lecture de fichiers (par plages de pages pour les longs textes), puis
citer les articles **tels qu'ils figurent dans le PDF**.

Conseils de recherche :
- chercher d'abord par **numéro** (`65.99`, `2.04.514`), puis par mots du titre ;
- le catalogue arabe est beaucoup plus complet et plus à jour que le français : en cas
  d'échec en français, chercher en arabe ;
- un titre commençant par « تم نسخ » signale un texte **abrogé** ;
- la colonne « updated » est la date de mise à jour du fichier sur Adala, pas la date de la loi.

## Règles

1. **Ne jamais citer un article de mémoire.** Lire le texte (skill spécialisé, `law.py`, ou PDF
   téléchargé) avant de citer. Si le texte est introuvable, le dire.
2. **L'arabe fait foi.** Les versions françaises d'Adala sont souvent plus anciennes : comparer
   les dates avant de s'y fier, et signaler toute traduction personnelle comme non officielle.
3. **Dater chaque réponse** : version consultée, date de mise à jour, lien source.
4. **Catalogue figé au 2026-11-19.** Un texte publié ensuite n'y figure pas. Pour une
   question sensible à l'actualité, le dire et inviter à vérifier sur Adala ou au Bulletin
   officiel (<https://www.sgg.gov.ma>).
5. **Jurisprudence : seules les décisions de la Cour constitutionnelle** figurent au catalogue
   (PDF à télécharger et à lire). Les arrêts de la Cour de cassation et des cours d'appel n'y
   sont pas : ne jamais inventer de référence d'arrêt, et le dire quand un point en dépend.
   Orienter vers le portail officiel gratuit du CSPJ
   (<https://juriscassation.cspj.ma/ar/Decisions/RechercheDecisions> : Cour de cassation,
   cours d'appel, premières instances) avec des mots-clés arabes ; l'utilisateur fait la
   recherche (code de confirmation), et un arrêt collé dans la conversation peut être analysé.
   Une circulaire n'est pas une loi : la citer comme circulaire, avec sa date.
6. Répondre dans la langue de l'utilisateur (arabe, français, darija ; à une question en darija
   écrite en lettres latines, répondre en darija dans la même écriture, pas en français). Pour un justiciable,
   informer puis recommander de consulter un avocat.
