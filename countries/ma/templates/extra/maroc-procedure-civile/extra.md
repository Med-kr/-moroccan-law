
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
