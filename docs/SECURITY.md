# Sécurité et confidentialité / الأمن والسرية

## Ce qui circule, et où

| Élément | Où il est traité | Qui en répond |
|---|---|---|
| Textes de loi, fiches, recherche, délais | Sur le poste ou le serveur du cabinet (aucun appel réseau) | moroccan-law |
| PDF officiel d'un texte (à la demande) | Téléchargé depuis adala.justice.gov.ma | Ministère de la Justice (source) |
| Question, réponse, documents envoyés à l'assistant | Chez le fournisseur d'IA choisi par le cabinet, avec **sa** clé | Le fournisseur (ses conditions) et le cabinet (son choix) |
| Historique, documents importés, décisions, clé IA | Base locale chiffrée (Web App) | Le cabinet (hébergement, sauvegardes) |

moroccan-law ne collecte rien, n'envoie aucune télémétrie et n'entraîne aucun modèle.

## Secret professionnel

L'avocat est tenu au secret professionnel (art. 46 de la loi 66.23). Recommandations :

1. Poser les questions en termes généraux ; ne pas saisir de nom, numéro de dossier, CIN, montant
   identifiant un client.
2. Avant d'importer un document client, le **pseudonymiser** (remplacer les noms par X, Y).
3. Pour les dossiers sensibles : fournisseur « compatible OpenAI » pointant sur un **modèle local**
   (LM Studio, Ollama) — rien ne quitte le cabinet.
4. Vérifier les conditions du fournisseur d'IA : conservation des données, usage pour l'entraînement,
   localisation. Les offres professionnelles des fournisseurs prévoient en général la non-utilisation
   des données pour l'entraînement ; c'est au cabinet de le vérifier pour son contrat.

## Mesures techniques (Web App)

- Écoute sur localhost par défaut ; HTTPS par un proxy devant pour un accès réseau (`MOROCCAN_LAW_HTTPS=1`).
- Comptes locaux, rôles administrateur / membre ; mots de passe PBKDF2-SHA256 (600 000 itérations) ;
  sessions de 12 h, cookie `HttpOnly`, `SameSite=Strict`.
- Chiffrement au repos (Fernet : AES-128-CBC + HMAC-SHA256) des conversations, documents, décisions et de
  la clé IA ; clé dans un fichier en droits 600 ou dans une variable d'environnement.
- Chaque utilisateur ne voit que ses conversations, documents et décisions.
- Suppression automatique après la durée de conservation fixée (90 jours par défaut).
- Journal d'audit (connexions, questions, imports, exports, suppressions, réglages) sans contenu.
- En-têtes de sécurité : CSP stricte sans script en ligne, `X-Frame-Options: DENY`, `nosniff`, pas de referrer.
- Interface sans `innerHTML` : un document ou une réponse ne peut pas injecter de code dans la page.
- Les entrées des outils appelés par l'IA sont validées avant exécution ; l'outil qui écrit des fichiers
  (téléchargement de PDF) est désactivé dans la Web App et en mode HTTP.

## Limites

- La sécurité du poste ou du serveur (mises à jour, sauvegardes, accès physique) relève du cabinet.
- Le chiffrement protège la base copiée sans la clé ; il ne protège pas contre un accès au serveur en marche.
- Pas encore d'authentification à deux facteurs ni d'intégration à un annuaire (prévues pour l'offre Cabinet).

## Signaler une faille

Ouvrir un ticket privé (« Security advisory ») sur le dépôt GitHub ; ne pas publier de détail d'exploitation.
