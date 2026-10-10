# Backend liO Occitanie — prototype

Le document `Specification_backend_liO_Occitanie.docx` décrit le modèle de données et le catalogue API complet.

## Démarrage rapide
1. Python 3.11+ et PostgreSQL.
2. `pip install -r requirements.txt`
3. Configurer `DATABASE_URL` depuis `.env.example`.
4. Importer les hébergements : `python scripts/import_accommodations.py --file data/occitanie-hebergements-scolaires.xlsx`
5. Démarrer : `uvicorn app.main:app --reload`
6. Swagger : `http://127.0.0.1:8000/docs`

## Principes
- Pas de formulaire classique : texte libre ou transcription Speech-to-Text.
- La gare de départ vient de l’enseignant.
- Les destinations proposées proviennent des données disponibles ; les données d’hébergement ne sont pas un catalogue complet de visites.
- La recherche ferroviaire renvoie une erreur explicite tant qu’une source d’horaires vérifiée n’est pas intégrée.
- Une demande est en attente, jamais une réservation confirmée automatiquement.
- Ce scaffold est une base de développement et doit être sécurisé avant la production.
