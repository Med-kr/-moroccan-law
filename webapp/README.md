# moroccan-law — application web locale / تطبيق محلي

Interface pour le cabinet : assistant juridique (arabe, français, darija), recherche dans les
813 textes, fiches d'articles, calcul des délais, documents du dossier, bibliothèque de décisions,
historique, export Word/PDF. **Tout reste sur le poste ou le serveur du cabinet.**

## Démarrer (Docker)

```bash
git clone https://github.com/Med-kr/moroccan-law.git && cd moroccan-law
docker compose -f webapp/docker-compose.yml up -d --build
```

Ouvrir <http://localhost:8642> (autre port : `MOROCCAN_LAW_PORT=9000 docker compose …`).
Au premier lancement, créer le compte administrateur, puis **Réglages** :

| Fournisseur | Ce qu'il faut |
|---|---|
| Anthropic (Claude) | la clé API du cabinet (console Anthropic) ; modèle par défaut `claude-opus-5-5`, effort `medium` |
| Compatible OpenAI | un modèle local (LM Studio : `http://host.docker.internal:1234/v1`, Ollama : `http://host.docker.internal:11434/v1`) ; rien ne sort du cabinet |

Sans clé, la recherche, les fiches et les délais fonctionnent ; seul l'assistant conversationnel est désactivé.

Sans Docker : `pip install -r webapp/requirements.txt` puis `uvicorn webapp.app:app --host 127.0.0.1 --port 8642`.

## Sécurité et confidentialité

- Écoute sur **localhost** uniquement ; pour le réseau du cabinet, placer un proxy HTTPS devant et
  mettre `MOROCCAN_LAW_HTTPS=1` (cookie `Secure`).
- Comptes locaux (administrateur / membre), mots de passe PBKDF2 (600 000 itérations), session de 12 h.
- Conversations, documents, décisions et clé IA **chiffrés au repos** (Fernet) ; clé dans
  `/data/secret.key` (droits 600) ou dans `MOROCCAN_LAW_SECRET` (`python -m webapp.store` en génère une).
- **Conservation** paramétrable (90 jours par défaut) : suppression automatique.
- **Journal d'audit** : qui a fait quoi et quand, jamais le contenu.
- Aucune télémétrie. Sorties réseau : le fournisseur d'IA choisi (avec la clé du cabinet) et, à la
  demande, le PDF officiel d'un texte sur adala.justice.gov.ma.
- Les questions et documents envoyés à l'assistant passent par le fournisseur d'IA choisi, selon ses
  conditions. Pour une confidentialité maximale : modèle local, ou anonymiser. Voir `docs/SECURITY.md`.

Le modèle Claude est appelé avec la reprise automatique côté serveur (`fallbacks: "default"`) :
si le modèle décline une demande, l'API la confie à un modèle de secours et l'interface l'indique.

## Tests

```bash
pip install -r webapp/requirements.txt
python -m unittest webapp.tests.test_webapp      # client Anthropic simulé : ni réseau, ni clé, ni coût
```
