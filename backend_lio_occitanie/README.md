# Backend Copilote Train liO Occitanie

API FastAPI du prototype de sorties scolaires. Voir [le démarrage frontend/backend](../README.md) et [l’analyse de cohérence](../docs/ANALYSE_COHERENCE.md).

## Routes utilisées par React

| Route | Comportement |
|---|---|
| `POST /api/v1/sessions` | Crée une session de projet. |
| `GET /api/v1/sessions/{id}` | Lit le projet et ses sélections. |
| `PATCH /api/v1/sessions/{id}` | Valide les données structurées, les dates et le groupe ≤ 50. Persiste les trains aller/retour ; un changement de trajet invalide les sélections. |
| `POST /api/trips/analyze` | Extraction pédagogique par règles, date précise et questions de clarification. Une session existante accumule le texte. |
| `POST /api/analyzeVoice` | Audio multipart → Whisper local → LLM local avec fallback heuristique ; renvoie la transcription et les catégories. |
| `POST /api/destinations/search` | Recherche dans les hébergements importés (57 dans la source fournie), avec filtres de thèmes/commune/département et provenance. |
| `POST /api/trains/search` | 503 sans source opérationnelle. `demo=true` active explicitement les données historiques. Date ISO obligatoire. |
| `POST /api/trips/summary` | Récapitulatif du projet sauvegardé, sans train par défaut inventé. |
| `POST /api/prereservations` | Enregistre une demande locale en attente et une copie du projet/itinéraire, avec référence. Aucun envoi SNCF ni email. |
| `POST /api/feedback` | Enregistre quatre notes et un commentaire liés à la session. |
| `GET /api/v1/accommodations` | Liste paginée des hébergements. |
| `GET /health` | Santé de l’API et de la base. |

Les alias versionnés historiques restent disponibles ; Swagger expose les contrats exacts sur `/docs`. Le frontend technique d’origine est conservé sur `/test`. Son formulaire de trains doit envoyer une date et `demo=true` pour consulter la démonstration.

## Données honnêtes

Le fichier `lio_train_schedules.json` est dérivé d’une journée type de `Détail desserte (1).xlsx`, fourni pour février–juin 2026. Il ne valide pas les horaires pour une date demandée. Le générateur produit les places sous option par un hash et injecte des moyennes de régularité si une circulation est absente du CSV. Le score mêle ces données et des hypothèses de capacité/accès : il est donc signalé comme score de démonstration. L’autorisation groupes de chaque circulation reste à vérifier auprès d’une source opérationnelle.

Les hébergements ne constituent pas un catalogue exhaustif de visites. Leurs gares sont provisoires et leurs distances sont à vol d’oiseau. L’API ne transforme plus ces distances en durée de marche et ne prétend pas vérifier le seuil d’accès de 20 minutes. Sans source fiable de durée, le filtre de durée indique qu’il n’a pas été appliqué.

Le plafond de 50 voyageurs est confirmé par le cadrage. L’API n’incrémente pas la jauge de démonstration lors d’une demande et ne place aucune option réelle. Les avis sont conservés ; leur agrégation dans le score reste à implémenter.

## Démarrage local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./data/lio.db
python scripts/import_accommodations.py --file data/occitanie-hebergements-scolaires.xlsx
uvicorn app.main:app --reload
```

`DATABASE_URL` est lu depuis l’environnement du processus. La création des tables existante est conservée ; aucune migration de colonnes n’est nécessaire, les nouveaux paramètres du projet étant stockés dans `structured_request` et la demande dans `selected_itinerary`.

`FRONTEND_ORIGINS` accepte une liste séparée par des virgules ; localhost et 127.0.0.1:5173 sont autorisés par défaut. Vite utilise un proxy `/api`, configurable avec `API_PROXY_TARGET`.

## Audio et LLM

`POST /api/analyzeVoice` reçoit `file` (WAV, WebM, MP3, OGG…) et `language` (fr par défaut). La réponse expose `transcription`, `nombre_personnes`, `date_depart`, `date_retour`, `lieu_depart`, `destination`, `destination_connue` et `speech_detected`. Le frontend présente le texte pour correction puis utilise le contrat d’analyse pédagogique commun.

Le modèle Whisper GGML doit être présent dans `models/` ou indiqué par `WHISPER_MODEL_PATH`. Le client LLM appelle llama.cpp ; en cas d’indisponibilité, l’extracteur de voyage utilise les règles de fallback. La recherche et le formulaire peuvent fonctionner sans ces modèles.

Depuis ce dossier, la stack existante se lance avec :

```bash
docker compose up --build
```

Trois services : téléchargement du modèle Qwen 2.5 GGUF, serveur llama.cpp sur 8080 et FastAPI/Whisper sur 8000. Le compose du dossier backend est la référence pour cette commande. Le frontend Vite se démarre séparément.

## Tests

```bash
pip install pytest
python -m pytest tests -q
```

Les tests de contrats utilisent SQLite isolée ; ils couvrent notamment l’absence de source opérationnelle, l’opt-in historique, les distances inconnues, les dates/effectifs invalides, les clarifications, la validation et l’invalidation des sélections, la persistance des demandes et la liaison des avis. Les modèles réels et le build Docker n’ont pas été exécutés lors de la validation locale.
