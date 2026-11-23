---
name: maroc-immobilier
description: >-
  Droit immobilier et baux / القانون العقاري والكراء — texte officiel arabe, article par article, extrait des
  PDF publiés par le ministère de la Justice du Maroc (portail Adala). À utiliser dès qu'une
  question porte sur le droit marocain dans ce domaine, qu'il faut citer, vérifier ou retrouver
  un article, rédiger une consultation, une requête, des conclusions ou un contrat fondés sur
  ces textes. Mots-clés : مدونة الحقوق العينية، التحفيظ العقاري، الرسم العقاري، التعرض، الملكية المشتركة، الكراء السكني والمهني، الكراء التجاري، الإفراغ، مراجعة السومة الكرائية، نزع الملكية — droits réels, immatriculation foncière, titre foncier, opposition, copropriété, bail d'habitation, bail commercial, éviction, révision du loyer, expropriation.
---

# Droit immobilier et baux — القانون العقاري والكراء

Ce skill contient le **texte intégral en arabe** des lois ci-dessous, tel que publié sur
[Adala](https://adala.justice.gov.ma) (ministère de la Justice). Construit le 2026-11-23.

| text | النص | Texte | حجم | صيغة محينة بتاريخ | source |
|---|---|---|---|---|---|
| `huquq-ayniya-39-08` | القانون رقم 39.08 المتعلق بمدونة الحقوق العينية | Loi 39-08 portant code des droits réels | 334 المادة | 16 يوليو 2026 | 2026-08-06 |
| `tahfid-aqari` | ظهير التحفيظ العقاري | Dahir sur l'immatriculation foncière | 134 الفصل | 23 يناير 2014 | 2026-07-29 |
| `milkiya-mushtaraka-18-00` | القانون رقم 18.00 المتعلق بنظام الملكية المشتركة للعقارات المبنية | Loi 18-00 relative au statut de la copropriété des immeubles bâtis | 101 المادة | 16 يوليو 2026 | 2026-07-29 |
| `kira-sakani-67-12` | القانون المتعلق بتنظيم العلاقات التعاقدية بين المكري والمكتري للمحلات المعدة للسكنى أو للاستعمال المهني | Loi sur les baux d'habitation et à usage professionnel | 75 المادة | 21 فبراير 2019 | 2026-04-15 |
| `kira-tijari-49-16` | القانون المتعلق بكراء العقارات أو المحلات المخصصة للاستعمال التجاري أو الصناعي أو الحرفي | Loi sur les baux commerciaux, industriels et artisanaux | 38 المادة | — | 2025-09-09 |
| `murajaat-kira` | القانون المتعلق بكيفية مراجعة أثمان الكراء | Loi sur la révision des loyers | 10 المادة | — | 2025-09-09 |
| `naz-milkiya-7-81` | القانون رقم 7.81 المتعلق بنزع الملكية لأجل المنفعة العامة | Loi 7-81 relative à l'expropriation pour cause d'utilité publique | 70 الفصل | 23 فبراير 2026 | 2026-07-29 |
| `huquq-ayniya-fr` | [نسخة فرنسية — قد لا تكون محينة] مدونة الحقوق العينية | [Version française — peut ne pas être à jour] Code des droits réels | 334 Article | — | 2025-11-25 |
| `tahfid-aqari-fr` | [نسخة فرنسية — قد لا تكون محينة] ظهير التحفيظ العقاري | [Version française — peut ne pas être à jour] Dahir sur l'immatriculation foncière | 123 Article | — | 2025-11-25 |
| `milkiya-mushtaraka-fr` | [نسخة فرنسية — قد لا تكون محينة] قانون الملكية المشتركة للعقارات المبنية | [Version française — peut ne pas être à jour] Statut de la copropriété des immeubles bâtis | 93 Article | 3 novembre 2016 | 2025-11-25 |
| `taamir-12-90` | القانون رقم 12.90 المتعلق بالتعمير | Loi 12-90 relative à l'urbanisme | 97 المادة | 19 سبتمبر 2016 | 2026-07-29 |
| `tajziat-25-90` | القانون رقم 25.90 المتعلق بالتجزئات العقارية والمجموعات السكنية وتقسيم العقارات | Loi 25-90 relative aux lotissements, groupes d'habitations et morcellements | 96 المادة | 10 أغسطس 2026 | 2026-10-02 |
| `ijar-mufdi-51-00` | القانون رقم 51.00 المتعلق بالإيجار المفضي إلى تملك العقار | Loi 51-00 relative à la location-accession à la propriété immobilière | 23 المادة | 16 يوليو 2026 | 2026-08-12 |
| `awqaf` | مدونة الأوقاف | Code des Habous | 177 المادة | 11 مارس 2019 | 2026-10-09 |

**Versions françaises.** Les textes dont l'identifiant se termine par `-fr` sont les versions
françaises publiées par Adala. Elles servent à répondre et à citer en français, mais elles sont
souvent **antérieures** à la version arabe : comparer les deux dates du tableau avant de s'en
servir. Si la version arabe est plus récente, lire l'article arabe, signaler l'écart de dates, et
ne présenter le texte français que comme version antérieure. En cas de divergence, l'arabe fait foi.

« صيغة محينة بتاريخ » est la date de consolidation imprimée dans le PDF officiel ; « Adala »
est la date de dernière mise à jour du fichier sur le portail.

## Règle n° 1 : ne jamais citer de mémoire

Tout article cité, résumé ou appliqué doit d'abord être **lu avec l'outil** :

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" list
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" article <text> 43 44 65-1 "85 مكرر"
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" article <text> 43..51        # plage
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" search الإخطار الفصل --text <text>
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" search préavis licenciement --text <text>-fr
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" toc <text>
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" card <text> 204       # statut : en vigueur, modifié, abrogé, ajouté + BO
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" both <text> 230       # arabe et français côte à côte
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" transitional <text>   # entrée en vigueur, abrogations, affaires en cours
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" info <text>
```

Si `${CLAUDE_SKILL_DIR}` n'est pas développé, utiliser le « Base directory for this skill »
affiché au chargement. Les fichiers sont aussi lisibles directement :
`references/<text>/text.md` (texte), `toc.md` (plan), `meta.json` (source et version).

- La recherche se fait **en arabe** dans les textes arabes et en français dans les textes `-fr`.
  Les résultats sont **classés par pertinence** (le premier est le plus probable, mais lire
  plusieurs résultats) ; elle ignore hamzas, voyelles, tā' marbūṭa, l'article et les prépositions
  attachés (« للأطر » = « الأطر ») et cherche aussi dans les intitulés. Si la question est en
  français ou en darija, traduire d'abord les notions **dans les mots de la loi** (« الطرد » →
  « الفصل », « الشرط الجزائي » → « التعويض المتفق عليه »), essayer plusieurs formulations ;
  les résultats marqués « جزئي » ne contiennent qu'une partie des mots.
- `NOT FOUND` signifie que l'article n'existe pas dans cette version (abrogé, renuméroté, ou
  autre texte). Le dire tel quel ; ne jamais reconstituer un article absent.
- Un article vide avec une note de bas de page est en général abrogé ou remplacé : lire la note.

## Méthode de réponse

1. **Qualifier** la question et repérer le ou les textes (`toc` puis `search`).
2. **Lire** les articles pertinents, ainsi que ceux auxquels ils renvoient et les notes `[^n]`
   (elles donnent les lois modificatives et les références au Bulletin officiel). Pour l'article
   décisif, lire sa **fiche** (`card`) et donner son statut (en vigueur tel que publié, modifié par la
   loi … — BO n° …, ajouté, abrogé).
3. **Répondre dans la langue de l'utilisateur** (arabe, français ou darija ; une question en
   darija écrite en lettres latines, « ch7al mn youm 3ndi… », reçoit une réponse en darija dans
   la même écriture, pas en français) en donnant pour
   chaque règle : le texte, le numéro d'article, et la citation arabe exacte des passages
   décisifs. Une traduction française est une traduction de travail, à signaler comme
   **non officielle** ; seul l'arabe fait foi.
4. **Dater** : indiquer la version utilisée (« صيغة محينة بتاريخ … ») et le lien source affiché
   par l'outil. **Application dans le temps** : dès que les faits, l'acte, le jugement ou la
   procédure peuvent être antérieurs au texte ou à sa dernière modification, lancer
   `law.py transitional <text>` et appliquer ce qu'il dit (ex. art. 643 de la loi 58.25 : les
   délais commencés avant l'entrée en vigueur continuent sous l'ancienne loi ; les voies de
   recours nouvelles ne s'appliquent pas aux jugements rendus avant). Ne jamais trancher par
   supposition ; si la date des faits manque, la demander ou donner les deux régimes.
   Si un article demandé est `NOT FOUND`, lire la note d'abrogation que l'outil affiche.
5. **Séparer** ce que dit le texte, l'interprétation proposée, et ce qui dépend de la
   jurisprudence ou de textes d'application.

## Limites à énoncer honnêtement

- **Pas de jurisprudence** ici ni de doctrine. Ne jamais citer un arrêt, un numéro de dossier
  ou une « jurisprudence constante » de mémoire. Si un point dépend de la jurisprudence :
  le dire, et orienter vers le portail officiel et gratuit du CSPJ,
  <https://juriscassation.cspj.ma/ar/Decisions/RechercheDecisions> (≈ 52 000 arrêts de la Cour
  de cassation ; chambres : 1 civile, 2 statut personnel et successions, 3 commerciale,
  4 administrative, 5 sociale, 6 pénale, 7 immobilière), en proposant des mots-clés arabes de
  recherche (numéro d'article + notion). Le portail demande un code de confirmation : la
  recherche est faite par l'utilisateur. S'il colle le texte d'un arrêt, l'analyser et le
  confronter aux articles lus avec l'outil.
- **Décrets et arrêtés d'application** : seuls ceux listés ci-dessus sont inclus. Pour les
  autres textes, utiliser le skill `maroc-droit` (catalogue de tous les textes d'Adala).
- **Extraction automatique** depuis des PDF : mise en page, tableaux et quelques espaces
  peuvent être altérés. `meta.json` liste les anomalies détectées (`anomalies`). Avant un
  dépôt au tribunal, vérifier la citation sur le PDF officiel (lien dans `info`) ou au
  Bulletin officiel.
- **Mises à jour** : le texte est à jour à la date indiquée, pas au-delà. Pour un enjeu
  important, vérifier sur Adala qu'aucune modification n'est intervenue depuis.
- **Délais** : `delais.py` (procédure civile) applique l'article 602 et les fêtes à date fixe ;
  les fêtes religieuses ne font l'objet que d'une alerte (date fixée par l'observation du
  croissant). Ne pas présenter un délai calculé comme certain sans ces réserves.
- **Avertissement** : réponse d'information juridique fondée sur les textes, pas une
  consultation. Le dire une fois, brièvement, en fin de réponse quand la réponse conduit à agir
  (délai, recours, rédaction d'acte).
- Ce skill assiste un professionnel du droit ; il ne remplace pas son analyse. Si
  l'utilisateur est un justiciable, donner l'information et recommander de consulter un avocat
  pour sa situation.
