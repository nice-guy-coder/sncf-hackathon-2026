# Copilote de Sorties Scolaires en Train liO — Occitanie

> **Hackathon SNCF For IA** : *« Dessine-moi une mobilité durable »*  
> Solution digitale pour transformer le projet pédagogique d'un enseignant en une sortie scolaire pertinente, réalisable, rassurante et pré-réservable en train liO.

---

## 🚀 Architecture Simplifiée & Speech-to-Text Whisper

Conformément à la spécification fonctionnelle et au schéma d'architecture, l'API est organisée autour de **endpoints métier directs** supportant la saisie écrite et l'entrée vocale via **WhisperAI local** :

```http
POST /api/trips/analyze-audio  -> Analyse directe d'un enregistrement vocal (WAV, WebM, MP3) via WhisperAI
POST /api/analyzeVoice         -> Transcription d'un fichier audio en texte via Whisper local
POST /api/trips/analyze        -> Analyse de la demande en texte libre (ou transcription)
POST /api/destinations/search  -> Suggestions de sites & hébergements liO en Occitanie
POST /api/trains/search        -> Horaires liO réels, Jauge groupe (50 pax) & Indice Confiance (/100)
POST /api/trips/summary        -> Récapitulatif global du voyage
POST /api/prereservations      -> Demande de pré-réservation (référence dossier + statut pending)
POST /api/feedback             -> Retour d'expérience après sortie pour nourrir l'indicateur
```

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

## 🐳 Déploiement Conteneurisé avec Docker

L'ensemble de la stack (serveur FastAPI/Uvicorn, base de données SQLite, modèle WhisperAI GGML et données liO) est entièrement conteneurisé.

### Démarrage en une seule commande

Depuis la racine du projet :
```bash
docker compose up --build
```

Ou depuis le dossier `backend_lio_occitanie` :
```bash
docker compose up -d --build
```

- **API & Swagger Docs** : `http://localhost:8000/docs`
- **Frontend de test** (toutes les routes + enregistrement micro) : `http://localhost:8000/test`
  > Le micro n'est autorisé par le navigateur qu'en contexte sécurisé : utilisez bien `localhost` (pas l'IP de la machine).
- **Santé / Healthcheck** : `http://localhost:8000/health`
- **Persistance** : la base SQLite est persistée dans le volume `./data/lio.db`.

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
