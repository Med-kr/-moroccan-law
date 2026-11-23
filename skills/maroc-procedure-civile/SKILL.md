---
name: maroc-procedure-civile
description: >-
  Procédure civile et organisation judiciaire / المسطرة المدنية والتنظيم القضائي — texte officiel arabe, article par article, extrait des
  PDF publiés par le ministère de la Justice du Maroc (portail Adala). À utiliser dès qu'une
  question porte sur le droit marocain dans ce domaine, qu'il faut citer, vérifier ou retrouver
  un article, rédiger une consultation, une requête, des conclusions ou un contrat fondés sur
  ces textes. Mots-clés : المسطرة المدنية، القانون 58.25، الاختصاص، المقال الافتتاحي، التبليغ، الاستئناف، النقض، التنفيذ، الحجز، قضاء القرب، التنظيم القضائي — procédure civile, loi 58-25, compétence, assignation, notification, appel, cassation, exécution, saisie, juridictions de proximité, organisation judiciaire.
---

# Procédure civile et organisation judiciaire — المسطرة المدنية والتنظيم القضائي

Ce skill contient le **texte intégral en arabe** des lois ci-dessous, tel que publié sur
[Adala](https://adala.justice.gov.ma) (ministère de la Justice). Construit le 2026-11-23.

| text | النص | Texte | حجم | صيغة محينة بتاريخ | source |
|---|---|---|---|---|---|
| `msm-58-25` | القانون رقم 58.25 المتعلق بالمسطرة المدنية | Loi 58-25 relative à la procédure civile | 644 المادة | — | 2026-09-09 |
| `tandim-qadai-38-15` | القانون رقم 38.15 المتعلق بالتنظيم القضائي | Loi 38-15 relative à l'organisation judiciaire | 111 المادة | 3 مارس 2025 | 2026-03-25 |
| `qada-qorb-42-10` | القانون رقم 42.10 المتعلق بتنظيم قضاء القرب | Loi 42-10 relative aux juridictions de proximité | 22 المادة | 23 فبراير 2026 | 2026-08-27 |
| `msm-1974-mansukh` | [منسوخ — للمقارنة فقط] قانون المسطرة المدنية القديم (الظهير الشريف بمثابة قانون رقم 1.74.447) | [ABROGÉ — pour comparaison uniquement] Ancien code de procédure civile (dahir portant loi 1-74-447) | 471 الفصل | — | 2026-09-17 |
| `mahakim-idariya-41-90-mansukh` | [منسوخ — للمقارنة فقط] القانون رقم 41.90 المحدث بموجبه محاكم إدارية | [ABROGÉ — pour comparaison uniquement] Loi 41-90 instituant des tribunaux administratifs | 47 المادة | — | 2026-09-17 |
| `mahakim-tijariya-53-95-mansukh` | [منسوخ — للمقارنة فقط] القانون رقم 53.95 القاضي بإحداث المحاكم التجارية | [ABROGÉ — pour comparaison uniquement] Loi 53-95 instituant des juridictions de commerce | 25 المادة | — | 2026-09-17 |
| `ayam-al-ayad-2-77-169` | المرسوم رقم 2.77.169 بتحديد لائحة أيام الأعياد المسموح فيها بالعطلة في الإدارات العمومية | Décret 2-77-169 fixant la liste des jours fériés dans les administrations publiques | 3 الفصل | 5 فبراير 2026 | 2026-06-11 |
| `ikrah-badani-1961` | الظهير الشريف بشأن استعمال الإكراه البدني في القضايا المدنية | Dahir relatif à l'exercice de la contrainte par corps en matière civile | 3 الفصل | 27 نوفمبر 2006 | 2025-12-15 |

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

## Outils pratiques de ce skill

### Ancien code ↔ loi 58-25 (comparaison)

La loi 58-25 a abrogé l'ancien code de procédure civile (dahir 1-74-447), la loi 41-90
(tribunaux administratifs) et la loi 53-95 (juridictions de commerce). Ces trois textes sont
inclus **uniquement pour comparer** : ne jamais les appliquer comme droit en vigueur sans avoir
lu les dispositions transitoires et finales de la loi 58-25.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/compare.py" msm-1974 134 --in msm-58-25     # ancien -> nouveau
python3 "${CLAUDE_SKILL_DIR}/scripts/compare.py" msm-58-25 204 --in msm-1974     # nouveau -> ancien
python3 "${CLAUDE_SKILL_DIR}/scripts/compare.py" table msm-1974 msm-58-25        # table complète
```

Le rapprochement est une **similarité textuelle calculée**, pas une table de concordance
officielle : présenter le résultat comme tel, lire les deux articles, puis décrire ce qui change
(délai, compétence, formalités) en citant les deux textes.

### Délais de procédure

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/delais.py" list الاستئناف --text msm-58-25   # articles fixant un délai
python3 "${CLAUDE_SKILL_DIR}/scripts/delais.py" calc --from 2026-11-03 --days 30
python3 "${CLAUDE_SKILL_DIR}/scripts/delais.py" calc --from 2026-11-03 --days 15 --electronic
python3 "${CLAUDE_SKILL_DIR}/scripts/delais.py" calc --from 2027-02-10 --months 1 --holidays 2027-03-10,2027-03-11
```

Toujours : (1) lire l'article qui fixe le délai et son point de départ, (2) lire l'article 602
(délais francs), (3) calculer avec l'outil, jamais de tête, (4) donner à l'utilisateur la date
calculée **et** la date de prudence affichée, (5) rappeler que les fêtes religieuses (calendrier
lunaire) ne sont pas connues de l'outil et doivent être passées avec `--holidays`. Les jours
fériés à date fixe viennent du décret 2-77-169 (texte `ayam-al-ayad-2-77-169`).

### Modèles d'actes

`assets/namadij/` contient trois trames en arabe, chaque mention obligatoire étant rattachée à
son article : `maqal-iftitahi.md` (requête introductive, art. 76-77), `maqal-istinafi.md`
(requête d'appel, art. 204 et 216), `maqal-naqd.md` (pourvoi en cassation, art. 377 et 380).
Les lire, relire les articles cités avec `law.py`, remplir toutes les mentions, et remettre à
l'utilisateur la liste de vérification finale. Ce sont des trames de travail, pas des actes
prêts à déposer.
