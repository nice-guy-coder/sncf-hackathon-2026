# Copilote de Sorties Scolaires en Train liO — Occitanie

> **Hackathon SNCF For IA** : *« Dessine-moi une mobilité durable »*  
> Solution digitale pour transformer le projet pédagogique d'un enseignant en une sortie scolaire pertinente, réalisable, rassurante et pré-réservable en train liO.

---

## 🚀 Architecture Simplifiée (Contrat d'API Direct)

Conformément à la spécification fonctionnelle et au schéma de flux du projet, l'API est organisée autour de **6 endpoints métier directs** :

```http
POST /api/trips/analyze        -> Analyse de la demande écrite/vocale et extraction des besoins
POST /api/destinations/search  -> Suggestions de sites & hébergements liO en Occitanie
POST /api/trains/search        -> Horaires liO réels, Jauge groupe (50 pax) & Indice Confiance (/100)
POST /api/trips/summary        -> Récapitulatif global du voyage
POST /api/prereservations      -> Demande de pré-réservation (référence dossier + statut pending)
POST /api/feedback             -> Retour d'expérience après sortie pour nourrir l'indicateur
```

*(Des alias rétrocompatibles `/api/v1/...` sont également maintenus).*

---

## 🎯 Les 3 Briques Métier Clés Implémentées

1. **Jauge Intelligente de Pré-réservation (Plafond 50 pax)**
   - Règle SNCF liO : 50 voyageurs maximum par train pour les groupes.
   - Contrôle instantané de la disponibilité restante en tenant compte des options existantes :
     $$\text{Places disponibles} = 50 - \text{Places sous option}$$
   - Alerte visuelle claire si la capacité restante est insuffisante pour l'effectif de la classe.

2. **Accessibilité Gare $\rightarrow$ Site Culturel / Nature**
   - Objectif pédagogique prioritaire : $\le 20\text{ minutes à pied}$ (avec marge de marche pour groupe scolaire).
   - Signalement automatique d'un point de vigilance au-delà de 20 minutes (nécessité d'un transport urbain ou d'une navette).

3. **Indicateur « Confiance Voyageur Scolaire » (/100)**
   - Un score transparent et explicable calculé à partir des données historiques réelles de ponctualité de la Région Occitanie (`Data_Hackathon.csv`) :
     * **Régularité historique du train liO** : jusqu'à 40 points
     * **Fiabilité & absence de suppressions** : jusqu'à 30 points
     * **Accessibilité piétonne directe ($\le 20\text{ min}$)** : 15 points
     * **Capacité groupe adaptée** : 15 points

---

## 📂 Données Exploitées

- `occitanie-hebergements-scolaires.xlsx` : hébergements scolaires, capacités, thématiques et gares les plus proches.
- `Détail desserte (1).xlsx` : circulations et dessertes horaires réelles du réseau liO Occitanie.
- `Data_Hackathon.csv` : historique de régularité, suppressions, fréquentation et retards des trains liO.
- `data/lio_train_schedules.json` : catalogue consolidé des liaisons directes liO avec statistiques de fiabilité associées.

---

## 🛠️ Démarrage Rapide

### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 2. Importer les hébergements
```bash
python scripts/import_accommodations.py --file data/occitanie-hebergements-scolaires.xlsx
```

*(Optionnel) Pour régénérer le catalogue horaire liO :*
```bash
python scripts/build_lio_schedules.py
```

### 3. Lancer l'API
```bash
uvicorn app.main:app --reload
```

- **Documentation Swagger interactive** : `http://127.0.0.1:8000/docs`
- **Vérification santé** : `http://127.0.0.1:8000/health`

---

## 🧪 Tests Automatisés

Exécuter la suite de tests unitaires et d'intégration :
```bash
python tests/test_backend.py
```
