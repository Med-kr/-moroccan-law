---
name: maroc-corpus
description: >-
  Autres lois marocaines (extraction automatique) / باقي القوانين المغربية (استخراج آلي) — 718 lois et dahirs marocains (texte officiel arabe,
  article par article, 21,987 articles) qui ne sont pas dans les skills `maroc-*`
  spécialisés : santé, enseignement, fonction publique, agriculture, élections, sécurité, affaires
  religieuses, industrie, énergie, culture, pêche, collectivités territoriales, institutions
  constitutionnelles, etc. Extraits automatiquement des PDF du portail Adala. À utiliser quand une
  question de droit marocain porte sur une loi absente des skills spécialisés. Mots-clés : قانون، ظهير، الصحة، التعليم، الوظيفة العمومية، الفلاحة، الانتخابات، الجماعات الترابية، الطاقة، الصيد البحري، الثقافة — loi, dahir, santé, enseignement, fonction publique, agriculture, élections, collectivités territoriales, énergie, pêche, culture.
---

# Autres lois marocaines (extraction automatique) — باقي القوانين المغربية (استخراج آلي)

**718 textes, 21,987 articles**, texte intégral arabe tel que publié sur
[Adala](https://adala.justice.gov.ma) (ministère de la Justice). Construit le 2026-11-23.

**Niveau de contrôle : extraction automatique.** Ces textes passent les mêmes extracteurs et des
contrôles automatiques (aucun article, texte vide, lettres lues comme des chiffres, chiffres
altérés par la police — dates impossibles —, structure non
reconnue : le texte est alors écarté, voir `data/corpus-excluded.json` du dépôt), mais ils n'ont
**pas été relus un par un** comme ceux des skills spécialisés. Le dire dans la réponse et inviter à
vérifier la citation sur le PDF officiel (lien affiché par l'outil) avant tout usage contentieux.
Si un skill `maroc-*` spécialisé couvre la question, il passe en premier.

## Règle n° 1 : ne jamais citer de mémoire

Trouver d'abord le texte par son titre, puis lire l'article avec l'outil :

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" find التعليم المدرسي          # textes dont le titre contient ces mots
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" toc <text>
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" article <text> 12 13 "5 مكرر"
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" search <mots arabes> --text <text>   # toujours avec --text ici
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" transitional <text>
python3 "${CLAUDE_SKILL_DIR}/scripts/law.py" info <text>
```

- `find` cherche dans les **titres** (arabe) ; essayer le numéro de la loi (« 51.17 ») ou un mot
  du titre. Sans résultat : le texte est peut-être un décret, une loi écartée par les contrôles ou
  absente d'Adala ; utiliser le catalogue du skill `maroc-droit` (PDF officiel).
- `search` sans `--text` parcourt les 718 textes : lent ; toujours cibler un texte.
- Résultats classés par pertinence ; ignorer hamzas, voyelles, article et prépositions attachés.

## Méthode de réponse

1. Identifier la loi (`find`), vérifier sa date de version (`info`) et lire les articles utiles
   et ceux auxquels ils renvoient, avec leurs notes `[^n]` (lois modificatives, Bulletin officiel).
2. Répondre dans la langue de l'utilisateur, avec le texte, le numéro d'article et la citation
   arabe exacte des passages décisifs ; une traduction est de travail, non officielle.
3. Dater la version et donner le lien source ; si les faits sont antérieurs au texte ou à une
   modification, lire `transitional`.
4. Signaler que le texte provient du corpus en extraction automatique non relue.

## Limites

- Pas de jurisprudence, pas de doctrine : ne jamais inventer un arrêt (voir `maroc-droit`).
- Décrets et arrêtés d'application : non inclus ici ; catalogue de `maroc-droit`.
- Lois de finances : écartées (polices des PDF qui lisent des lettres comme des chiffres).
- Information juridique, pas une consultation ; pour un justiciable, recommander un avocat.
