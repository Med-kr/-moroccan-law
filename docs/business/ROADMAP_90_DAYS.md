# Feuille de route — 90 jours

État au départ (23/11/2026) : 813 textes, 41 410 articles, fiches d'articles, recherche, délais,
serveur MCP, Web App locale (Docker), benchmark public partiel, 110+ tests.

## Jours 1–30 : confiance et données
- [ ] Benchmark public complet (115 cas, avec / sans outil) puis publication de `docs/BENCHMARK.md`.
- [ ] Relecture par 3 avocats indépendants de la grille de 60 questions (`docs/LAWYER_REVIEW.md`) ;
      chaque réponse notée C ou D devient un test.
- [ ] Envoi de la lettre au CSPJ (`docs/CSPJ_LETTER.md`) ; relance à J+21.
- [ ] Décrets d'application (≈ 3 370) dans le corpus, avec les mêmes contrôles.
- [ ] Recherche sémantique dans la Web App (modèle d'embeddings local) : objectif ≥ 90 % de bons articles
      dans les 5 premiers résultats sur le jeu scellé `holdout2`.

## Jours 31–60 : produit
- [ ] Web App : authentification à deux facteurs, dossiers partagés, modèles de mise en demeure et de contrats.
- [ ] Installateur Windows (un clic) pour les cabinets sans informaticien.
- [ ] Version hébergée de démonstration (données fictives uniquement).
- [ ] Mise à jour hebdomadaire des textes vérifiée en production (GitHub Actions).

## Jours 61–90 : lancement
- [ ] 10 à 20 avocats pilotes, 4 semaines d'usage réel (questions anonymisées).
- [ ] Entretiens de fin de pilote : temps gagné, erreurs vues, prix acceptable.
- [ ] Lancement de l'offre Pro au prix validé ; publication des résultats du pilote et du benchmark.
- [ ] Démo vidéo (2 minutes) : question en darija → article → source officielle.

Indicateurs suivis chaque semaine : avocats actifs, questions par avocat, part des réponses citant une
source ouverte par l'utilisateur, erreurs signalées et délai de correction.
