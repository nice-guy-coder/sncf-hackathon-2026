# Copilote de Sorties Scolaires en Train liO — Occitanie

> **Hackathon SNCF For IA** : *« Dessine-moi une mobilité durable »*  
> Solution digitale pour transformer le projet pédagogique d'un enseignant en une sortie scolaire pertinente, réalisable, rassurante et pré-réservable en train liO.

---

## 🚀 Architecture Intégrée : WhisperAI + LLM Local + Backend liO

Conformément à la spécification fonctionnelle et à l'architecture cible, l'API orchestre la chaîne complète d'acquisition vocale, de compréhension du langage naturel (LLM local) et de recherche ferroviaire :

```http
POST /api/analyzeVoice         -> Audio (micro) -> Whisper local -> LLM local (Qwen2.5) -> JSON structuré
POST /api/trips/analyze        -> Analyse de projet pédagogique en texte libre (thèmes, effectifs, dates)
POST /api/destinations/search  -> Suggestions de sites & hébergements scolaires liO en Occitanie
POST /api/trains/search        -> Horaires liO réels, Jauge groupe (50 pax) & Indice Confiance (/100)
POST /api/trips/summary        -> Récapitulatif global du projet de voyage
POST /api/prereservations      -> Demande de pré-réservation (référence dossier + statut pending)
POST /api/feedback             -> Retour d'expérience après sortie pour nourrir l'indicateur
```

### Route vocale `/api/analyzeVoice`
1. Reçoit le flux audio (WAV, WebM, MP3, OGG...).
2. Transcrit l'audio via **WhisperAI** local (`ggml-base-q5_1`).
3. Envoie la transcription en entrée au **LLM local** (Qwen 2.5 Instruct via serveur llama.cpp).
4. Retourne les catégories extraites en JSON :
   - `transcription` (texte brut retranscrit)
   - `nombre_personnes` (int ou `null`)
   - `date_depart` (format ISO `YYYY-MM-DD` ou `null`)
   - `date_retour` (format ISO `YYYY-MM-DD` ou `null`)
   - `lieu_depart` (str ou `null`)
   - `destination` (str ou `null`)
   - `destination_connue` (bool)
   - `speech_detected` (bool)

> **Résilience & Fallback** : Si le serveur LLM est indisponible ou non démarré, le backend bascule automatiquement sur l'extracteur heuristique sans interrompre le service.

---

## 🎯 Les 3 Briques Métier Clés Implémentées

1. **Jauge Intelligente de Pré-réservation (Plafond 50 pax)**
   - Règle SNCF liO : 50 voyageurs maximum par train pour les groupes.
   - Contrôle instantané de la disponibilité restante en tenant compte des options existantes :
     $$\text{Places disponibles} = 50 - \text{Places sous option}$$
   - Alerte visuelle claire si la capacité restante est insuffisante pour l'effectif de la classe.

2. **Accessibilité Gare $\rightarrow$ Site Culturel / Nature**
   - Objectif pédagogique prioritaire : $\le 20\text{ minutes à pied}$ (avec marge de marche pour groupe scolaire).
   - Signalement automatique d'un point de vigilance au-delà de 20 minutes (transport urbain ou navette requise).

3. **Indicateur « Confiance Voyageur Scolaire » (/100)**
   - Un score transparent et explicable calculé à partir des données historiques réelles de ponctualité liO (`Data_Hackathon.csv`) :
     * **Régularité historique du train liO** : jusqu'à 40 points
     * **Fiabilité & absence de suppressions** : jusqu'à 30 points
     * **Accessibilité piétonne directe ($\le 20\text{ min}$)** : 15 points
     * **Capacité groupe adaptée** : 15 points

---

## 🐳 Déploiement Conteneurisé Multi-Services avec Docker Compose

L'ensemble de la stack est orchestré via Docker Compose en 3 services coordonnés :
1. **`model-downloader`** : Télécharge automatiquement le modèle LLM Qwen 2.5 (GGUF quantifié) dans le volume partagé `llm_models` s'il n'est pas déjà en cache.
2. **`llm`** : Serveur d'inférence llama.cpp CPU (`ghcr.io/ggml-org/llama.cpp:server`) compatible API OpenAI sur le port 8080.
3. **`backend`** : Serveur FastAPI / Uvicorn avec WhisperAI GGML, base de données SQLite, données liO et frontend de test.

### Démarrage en une seule commande

Depuis la racine du projet ou depuis le dossier `backend_lio_occitanie` :
```bash
docker compose up --build
```

- **Frontend de test interactif** (enregistrement micro + test de toutes les routes) : `http://localhost:8000/test`
  > Le micro n'est autorisé par le navigateur qu'en contexte sécurisé : utilisez bien `localhost` (ou 127.0.0.1).
- **Documentation OpenAPI / Swagger** : `http://localhost:8000/docs`
- **Serveur LLM llama.cpp** : `http://localhost:8080/health`
- **Santé Backend** : `http://localhost:8000/health`
- **Persistance** :
  - Base SQLite : `./data/lio.db`
  - Modèles LLM : volume Docker `llm_models`
  - Modèle Whisper : téléchargé automatiquement lors du build Docker

---

## 🛠️ Démarrage Local (sans Docker)

### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 2. Importer les hébergements
```bash
python scripts/import_accommodations.py --file data/occitanie-hebergements-scolaires.xlsx
```

### 3. Lancer l'API
```bash
uvicorn app.main:app --reload
```

---

## 🧪 Tests Automatisés

Exécuter la suite de tests unitaires et d'intégration :
```bash
python tests/test_backend.py
```
