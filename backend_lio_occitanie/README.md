# Backend Copilote Train liO Occitanie

API FastAPI du prototype de sorties scolaires. Voir [le démarrage frontend/backend](../README.md) et [l’analyse de cohérence](../docs/ANALYSE_COHERENCE.md).

## Routes utilisées par React

| Route | Comportement |
|---|---|
| `POST /api/v1/sessions` | Crée une session de projet. |
| `GET /api/v1/sessions/{id}` | Lit le projet et ses sélections. |
| `PATCH /api/v1/sessions/{id}` | Valide les données structurées, les dates et le groupe ≤ 50. Persiste les trains aller/retour ; un changement de trajet invalide les sélections. |
| `POST /api/trips/analyze` | LLM avec pré-prompt pédagogique, validation JSON, dates normalisées et clarification ; règles de repli explicites si indisponible. Une session existante accumule le texte. |
| `POST /api/analyzeVoice` | Audio multipart → Whisper local → LLM local avec fallback heuristique ; renvoie la transcription et les catégories. |
| `POST /api/destinations/search` | Recherche dans le catalogue autonome de 26 attractions : rayon géographique autour d’une gare connue, ou un seul thème si inconnue. |
| `POST /api/trains/search` | 503 sans source opérationnelle. `demo=true` active explicitement les données historiques. Date ISO obligatoire. |
| `POST /api/trips/summary` | Récapitulatif du projet sauvegardé, sans train par défaut inventé. |
| `POST /api/prereservations` | Enregistre une demande locale en attente et une copie du projet/itinéraire, avec référence. Aucun envoi SNCF ni email. |
| `POST /api/feedback` | Enregistre quatre notes et un commentaire liés à la session. |
| `GET /api/v1/accommodations` | Liste paginée des hébergements. |
| `GET /health` | Santé de l’API et de la base. |

Les alias versionnés historiques restent disponibles ; Swagger expose les contrats exacts sur `/docs`. Le frontend technique d’origine est conservé sur `/test`. Son formulaire de trains doit envoyer une date et `demo=true` pour consulter la démonstration.

## Données honnêtes

Le fichier `lio_train_schedules.json` est dérivé d’une journée type de `Détail desserte (1).xlsx`, fourni pour février–juin 2026. Il ne valide pas les horaires pour une date demandée. Le générateur produit les places sous option par un hash et injecte des moyennes de régularité si une circulation est absente du CSV. Le score mêle ces données et des hypothèses de capacité/accès : il est donc signalé comme score de démonstration. L’autorisation groupes de chaque circulation reste à vérifier auprès d’une source opérationnelle.

Le catalogue `data/known_destinations_catalog.json` est distinct des hébergements. 17 sites disposent de coordonnées issues de fiches touristiques officielles (dont Sainte-Cécile, donnée de l’office d’Albi publiée via Cirkwi). `data/stations_occitanie.json` contient 274 gares voyageurs issues de SNCF Open Data, sous ODbL. Le moteur calcule la distance géodésique à vol d’oiseau (Haversine), trie les résultats autour de la gare et applique le rayon demandé. Les 9 sites sans coordonnées sont proposés uniquement par thème. L’API ne transforme plus ces distances en durée de marche et ne prétend pas vérifier le seuil d’accès de 20 minutes. Sans source fiable de durée, le filtre de durée indique qu’il n’a pas été appliqué.

Le plafond de 50 voyageurs est confirmé par le cadrage. L’API n’incrémente pas la jauge de démonstration lors d’une demande et ne place aucune option réelle. Les avis sont conservés ; leur agrégation dans le score reste à implémenter.

## Démarrage local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./data/lio.db
uvicorn app.main:app --reload
```

`DATABASE_URL` est lu depuis l’environnement du processus. La création des tables existante est conservée ; aucune migration de colonnes n’est nécessaire, les nouveaux paramètres du projet étant stockés dans `structured_request` et la demande dans `selected_itinerary`.

`FRONTEND_ORIGINS` accepte une liste séparée par des virgules ; localhost et 127.0.0.1:5173 sont autorisés par défaut. Vite utilise un proxy `/api`, configurable avec `API_PROXY_TARGET`.

## Audio et LLM

`POST /api/analyzeVoice` reçoit `file` (WAV, WebM, MP3, OGG…) et `language` (fr par défaut). La réponse expose `transcription`, `nombre_personnes`, `date_depart`, `date_retour`, `lieu_depart`, `destination`, `destination_connue` et `speech_detected`. Le frontend présente le texte pour correction puis utilise le contrat d’analyse pédagogique commun.

Le modèle Whisper GGML doit être présent dans `models/` ou indiqué par `WHISPER_MODEL_PATH`. Le client LLM appelle llama.cpp ; en cas d’indisponibilité, l’analyse commune utilise les règles de fallback et expose `analysis_mode=rules_fallback`, `analysis_warning` et `pedagogical_profile=null`. La recherche et le formulaire peuvent fonctionner sans ces modèles.

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

## Contrat pédagogique et attractions

`app/llm/school.py` contient `PEDAGOGICAL_SYSTEM_PROMPT` et les modèles de validation des cinq blocs demandés. Chaque appel LLM utilise un message `system` comprenant ce pré-prompt et un message `user` contenant la demande (texte ou transcription Whisper). La réponse contrainte est `{travel: {...}, pedagogical_profile: {...}}` pour conserver aussi les critères ferroviaires. Les profils incomplets ou invalides ne sont pas conservés comme analyse LLM.

Le client réserve au moins 1536 tokens de sortie. Docker configure désormais une fenêtre de contexte de 8192 tokens ; pour une instance llama.cpp externe, prévoir également suffisamment de contexte. `LLM_BASE_URL` vaut `http://llm:8080` dans Docker ; utiliser `http://127.0.0.1:8080` si llama.cpp tourne directement sur la machine.

`POST /api/destinations/search` accepte `search_mode=station` avec `destination_station` et `radius_km` (5 par défaut, 0,1–100), ou `search_mode=theme` avec exactement un thème. Une gare ambiguë/inconnue entraîne une erreur 422. Le catalogue est limité aux sites fournis, sans calcul d’itinéraire ni disponibilités.

`selected_destination_id` est conservé dans le JSON de session et dans la demande. Les colonnes et routes d’hébergements restent accessibles à titre historique ; le parcours React ne les utilise plus. Les données existantes d’hébergements ne sont ni supprimées ni migrées en attractions.

Sources : [référentiel SNCF des gares](https://data.sncf.com/explore/dataset/liste-des-gares/), [musées en Occitanie](https://www.tourisme-occitanie.com/loisirs/visites/musees/), [château et remparts de Carcassonne](https://www.tourisme-carcassonne.fr/activite-loisir/chateau-et-remparts-de-la-cite-de-carcassonne/). Les URL propres à chaque site et à ses coordonnées figurent dans le catalogue.

## Adéquation pédagogique et trajet piéton

Chaque résultat expose `pedagogical_assessment` : score indicatif sur 100, couverture des critères, détail des points, intérêt pédagogique, argumentaire et références officielles. Le calcul dans `app/visit_pedagogy.py` compare le projet au descriptif et aux thèmes du lieu : thème (50 points), disciplines (20), domaines du socle (15), notions/mots-clés (15). Les critères absents ne rapportent aucun point et la couverture est affichée. Sans profil LLM, un thème compatible donne 50/100, identifié comme évaluation partielle ; sans critères, le score est `null`. La classe contextualise le texte, sans certifier une correspondance à un programme. Les pistes de travail suggérées ne décrivent pas des ateliers réservables.

Le profil de session est utilisé lorsqu’il correspond à la classe et au thème actuels. Le calcul n’exige pas de nouvel appel LLM pour chaque lieu. L’argumentaire et le pré-prompt citent la [circulaire du 16 juillet 2024](https://www.education.gouv.fr/bo/2024/Hebdo30/MENE2407159C), qui a abrogé celle du 13 juin 2023. La préparation, le travail sur place et la restitution constituent une proposition pédagogique. L’enseignant doit préciser les programmes et les modalités d’autorisation ; le socle n’est pas présenté comme une validation acquise.

`GET /api/destinations/{id}/walking` utilise le profil **pedestrian** de l’[API IGN Géoplateforme](https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/calcul-itineraire/), depuis la gare géographiquement la plus proche dans le référentiel SNCF. Il retourne `closest_station`, `estimated_walking_minutes` (arrondi supérieur), `walking_distance_m`, la date et la version de la ressource IGN. Cette gare peut différer de celle choisie pour la recherche ; les deux sont alors indiquées. La proximité ne confirme pas les dessertes à la date du projet.

Les 17 lieux géolocalisés ont été calculés auprès de l’IGN. `data/walking_routes.json` conserve ces résultats datés (16 itinéraires distincts, Carcassonne et son château partageant les coordonnées). Le cache utilise les coordonnées exactes et l’identifiant de gare. Pour renouveler les instantanés :

```bash
python scripts/cache_walking_routes.py
```

Les nouvelles coordonnées déclenchent un calcul réseau avec délai de 8 secondes et 4 départs de requête par seconde. Sans coordonnées ou en cas d’échec, la durée reste inconnue ; aucune conversion de distance à vol d’oiseau n’est utilisée. Un recalage supérieur à 300 mètres est rejeté. Les estimations n’intègrent ni le rythme d’une classe, ni les fermetures locales, ni une validation PMR.

### Analyse des attractions par le LLM local et sources Web

Les cartes appellent `POST /api/destinations/{id}/assessment` avec les mêmes critères que la recherche (`session_id`, `themes`, `class_level`). Le backend récupère les pages HTTPS du site/source officiel enregistré dans le catalogue et jusqu'à deux liens vers des ressources scolaires découverts sur ces domaines. Il consulte aussi les références de l'Éducation nationale. Il ne s'agit pas d'un moteur de recherche Internet général et aucun fournisseur de recherche payant n'est requis.

Ces extraits et le profil pédagogique de la session (issu du texte ou de Whisper) sont transmis au serveur llama.cpp via `LLM_BASE_URL`. Le modèle fournit une analyse JSON validée : adéquation des quatre critères, explications, argumentaire et URL consultées. Le backend applique les pondérations 50/20/15/15 et n'accorde aucun point aux critères absents. Les URL inventées, réponses invalides et références manquantes provoquent un retour explicite à l'évaluation provisoire du catalogue. Les activités proposées sont distinguées des ateliers attestés ; le résultat reste indicatif.

L'interface affiche les résultats progressivement, les sources, la date d'évaluation, les incertitudes et un bouton pour réessayer en cas d'échec. Les appels sont mis en file pour le serveur local configuré avec une seule séquence d'inférence. Une analyse peut prendre plusieurs minutes pour une liste de lieux lors de la première consultation.

Le cache des pages et des évaluations est valable sept jours par défaut. Sa clé inclut le lieu, le thème, la classe et le profil pédagogique. Configuration :

- `PEDAGOGY_CACHE_DIR` : dossier du cache (Docker : `/app/data/pedagogy-cache`, persistant dans le volume `data`).
- `PEDAGOGY_CACHE_TTL_S` : durée de validité, par défaut `604800`.
- `LLM_MODEL_REVISION` : valeur à changer lorsque le modèle est remplacé pour invalider ses anciennes évaluations.
- `LLM_BASE_URL`, `LLM_TIMEOUT_S` : connexion et délai du serveur local.

Pour charger le changement avec Docker : `docker compose up -d --build backend` depuis `backend_lio_occitanie`. Hors Docker, définir `LLM_BASE_URL=http://localhost:8080` si llama.cpp écoute sur ce port, puis redémarrer le backend. Le backend doit pouvoir accéder aux sites officiels sur Internet. Les sites dynamiques, documents PDF, pages bloquées ou indisponibles ne sont pas automatiquement analysés ; leurs informations restent à confirmer. Pour vider le cache, supprimer uniquement le contenu du dossier configuré.

Lorsque les pages de l'Éducation nationale refusent les appels HTTP (403 notamment), le backend utilise les synthèses éditoriales de `data/pedagogical_references.json`, vérifiées le 10 octobre 2026 et liées aux textes officiels. Cette utilisation est explicitement signalée parmi les informations à confirmer et dans les métadonnées des sources (`retrieval_mode=verified_local_summary`). Ces synthèses doivent être revérifiées lors d'un changement réglementaire ; elles ne constituent pas une copie exhaustive des textes.
