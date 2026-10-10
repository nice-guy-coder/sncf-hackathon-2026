# AUTEURS DU PROJET
Matthias LOUBET matt.loubet@gmail.com <br>
Narayan BHATTARAI nbarpan11@gmail.com <br>
Sujan Man MANANDHAR  sujanmanpr@gmail.com <br>
Madxence SEJEAN madxence.sejean@hotmail.com <br>
Ciça COTRIM cicacotrim@gmail.com <br>

# Copilote de sorties scolaires en train liO — Occitanie

Frontend React/TypeScript/Vite et backend FastAPI. Le parcours couvre la description du projet (texte, voix, formulaire), les attractions touristiques, la recherche historique aller/retour, le récapitulatif, la demande locale et le feedback.

## Démarrage

Terminal backend, depuis la racine du dépôt :

```bash
cd backend_lio_occitanie
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./data/lio.db
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Le formulaire fonctionne sans LLM. Le chat et la transcription sont envoyés au LLM avec le pré-prompt pédagogique ; si le serveur est indisponible, l’application signale une extraction de base sans profil pédagogique. Pour un serveur LLM local hors Docker, définir `LLM_BASE_URL=http://127.0.0.1:8080`. L’audio exige Whisper, son modèle GGML et les dépendances audio. La stack Docker existante peut aussi être lancée depuis `backend_lio_occitanie` avec `docker compose up --build`.

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

Le catalogue de visites contient 26 attractions, avec des sources touristiques ; 17 disposent de coordonnées vérifiées. Le référentiel SNCF comprend 274 gares voyageurs d’Occitanie. Une destination connue déclenche une recherche dans un rayon de 5 km à vol d’oiseau, réglable. Une destination inconnue nécessite un seul thème pédagogique. Chaque carte présente une adéquation explicable et un argumentaire pédagogique/réglementaire. Les 17 lieux géolocalisés disposent aussi d’une estimation de marche issue d’un itinéraire piéton IGN. Ce catalogue est une sélection, sans disponibilités de visite ni connecteur ferroviaire opérationnel. Le mode historique est une démonstration volontaire, avec jauge simulée, et ne confirme aucun horaire ou disponibilité. Les demandes sont enregistrées localement ; aucun envoi SNCF ou email automatique n’a lieu. Les modèles vocaux/LLM réels n’ont pas été exécutés lors de la validation locale.

Les attractions peuvent maintenant être évaluées par le LLM local à partir de pages Web officielles et du projet pédagogique de la classe. L'analyse est progressive, sourcée et mise en cache ; une évaluation provisoire reste disponible si la recherche ou le modèle échoue. Voir la configuration dans [le README backend](backend_lio_occitanie/README.md).
