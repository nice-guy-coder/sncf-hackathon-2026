# Copilote de sorties scolaires en train liO — Occitanie

Frontend React/TypeScript/Vite et backend FastAPI. Le parcours couvre la description du projet (texte, voix, formulaire), les hébergements, la recherche historique aller/retour, le récapitulatif, la demande locale et le feedback.

## Démarrage

Terminal backend, depuis la racine du dépôt :

```bash
cd backend_lio_occitanie
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./data/lio.db
python scripts/import_accommodations.py --file data/occitanie-hebergements-scolaires.xlsx
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Le serveur texte/formulaire n’a pas besoin d’un modèle LLM actif. L’audio exige Whisper, son modèle GGML et les dépendances audio. La stack Docker existante peut aussi être lancée depuis `backend_lio_occitanie` avec `docker compose up --build`.

Terminal frontend, depuis la racine du dépôt :

```bash
cd frontend_lio_occitanie
npm ci
npm run dev
```

- Application : http://localhost:5173
- API : http://localhost:8000/docs
- Santé : http://localhost:8000/health

Voir [le rapport de cohérence](docs/ANALYSE_COHERENCE.md) et [le guide frontend](frontend_lio_occitanie/README.md).

## Validation

```bash
cd backend_lio_occitanie
python -m pytest tests -q
```

Installer `pytest` en complément des dépendances backend. Pour les parcours navigateur, démarrer les deux serveurs avec une base de test et suivre le guide frontend.

## État du prototype

Les 57 structures viennent du classeur fourni. Aucun catalogue exhaustif de visites ni connecteur ferroviaire opérationnel n’est présent. Le mode historique est une démonstration volontaire, avec jauge simulée, et ne confirme aucun horaire ou disponibilité. Les demandes sont enregistrées localement ; aucun envoi SNCF ou email automatique n’a lieu. Les modèles vocaux/LLM réels n’ont pas été exécutés lors de la validation locale.
