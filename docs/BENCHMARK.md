# Benchmark public / المقياس العمومي

**Statut : partiel.** La première exécution (23/11/2026, Claude Sonnet 5.5) a été interrompue par la limite
d'usage du compte : 157 exécutions sur 230 n'ont pas atteint le modèle. Elles **ne sont pas comptées**
(ni réussies, ni échouées). La mesure complète sera publiée ici, avec les réponses brutes.

## Méthode

115 cas (`bench/cases/`, générés par `bench/make_cases.py`), chacun posé deux fois au même modèle :
**avec** l'outil (plugin moroccan-law) et **sans**. Chaque réponse se termine par quatre lignes imposées
(article, loi, citation, statut), ce qui permet une notation automatique et vérifiable (`bench/score.py`).

| Mesure | Question posée | Comment c'est noté |
|---|---|---|
| **Retrieval** (60 cas) | Questions de praticien en darija, français, arabe | L'article attendu figure sur la ligne « المادة » |
| **Citation** (mêmes 60 cas) | — | Le passage cité existe **mot pour mot** dans le texte officiel (6 mots au moins) |
| **Actualité** (20 cas) | Articles abrogés ou modifiés, tirés des fiches d'articles | La ligne « الحالة » dit abrogé / modifié |
| **Hallucination** (20 pièges) | Article inexistant, loi inventée, demande d'un numéro d'arrêt | La réponse dit que cela n'existe pas / n'est pas disponible, sans inventer de numéro |
| **Raisonnement** (15 cas) | Un chiffre à calculer à partir des articles (indemnité, délai, durée) | Le résultat attendu figure dans la réponse |

Toutes les réponses attendues ont été **lues dans l'article** avant l'exécution ; aucune ne vient de mémoire.
Les cas sont figés dans le dépôt : on ne les modifie que pour corriger une erreur de cas, jamais pour
améliorer un score.

## Résultats partiels (réponses valides seulement)

| Mesure | Avec l'outil | Sans |
|---|---|---|
| Actualité (article abrogé ou modifié signalé comme tel) | **17 / 20** | 1 / 20 |
| Absence d'hallucination (cas notables) | **16 / 16** | 15 / 17 |
| Retrieval, citation, raisonnement | à mesurer | à mesurer |

## Ce que cela ne mesure pas

- Le raisonnement juridique complet : c'est le rôle de la relecture par des avocats indépendants
  (`docs/LAWYER_REVIEW.md`, notation A–D), sur des questions que le système n'a jamais vues.
- La variance d'une exécution à l'autre (une seule exécution par cas).

## Relecture indépendante

Tout avocat peut reprendre la grille, poser les questions et noter les réponses ; les grilles remplies sont
publiées (anonymisées si souhaité) et chaque réponse notée C ou D devient un test automatique.
