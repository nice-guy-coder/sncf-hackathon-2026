# Frontend Copilote liO Occitanie

Application React 19, TypeScript et Vite 7. Node.js 20.19+ ou 22.12+.

```bash
cd frontend_lio_occitanie
npm ci
npm run dev
```

Ouvrir http://localhost:5173. Le proxy Vite relaie `/api` et `/health` à FastAPI sur `http://127.0.0.1:8000`. Copier `.env.example` dans `.env` pour modifier `API_PROXY_TARGET`. Pour un frontend hébergé séparément, configurer `VITE_API_BASE_URL` et les `FRONTEND_ORIGINS` du backend. Ces variables frontend sont publiques ; aucun secret ne doit y être ajouté.

```bash
npm run build
npm run preview
```

Le serveur de preview ne fournit pas le proxy de développement : utiliser `VITE_API_BASE_URL` au moment du build, ou placer frontend et API derrière un même reverse proxy. Le dossier `dist` contient le résultat de compilation.

## Accès aux données

Le navigateur obtient les lieux uniquement par `POST /api/destinations/search` et les trains par `POST /api/trains/search`. `src/api.ts` porte les requêtes HTTP ; `src/useDestinations.ts` charge le catalogue depuis l’API à l’ouverture de `#suggestions`, à son rechargement et lors des changements de filtre. Les réponses ne sont pas remplacées par un catalogue local si le backend est indisponible : une erreur et un bouton Réessayer apparaissent.

Les fichiers Excel/CSV, leurs imports et la base de données sont gérés exclusivement par le backend. Aucun catalogue n’est embarqué dans React ni enregistré dans le stockage du navigateur. Les noms de fichiers ne sont pas affichés dans les cartes/détails : l’interface présente les lieux et la date de mise à jour du catalogue.

La configuration habituelle cible le backend Docker sur le port 8000. Le serveur temporaire sur 8011 et le proxy de test de l’aperçu ont été arrêtés après validation ; ils ne sont pas nécessaires au lancement de l’application.

## Parcours

Accueil → choix du mode → chat écrit/vocal ou formulaire → confirmation du projet et de la gare → destination connue ou hébergements suggérés → détails → recherche aller/retour → sélection et comparaison visuelle → récapitulatif → coordonnées → demande locale en attente → retour d’expérience.

Les demandes et avis sont écrits dans la base backend. Le brouillon du projet est conservé dans le `sessionStorage` de l’onglet, sans coordonnées de contact. Les résultats doivent être recherchés à nouveau après rechargement. Les écrans utilisent les styles des 22 prototypes HTML ; les variantes mobiles sont appliquées par media queries. Le logo liO et la photo d’accueil sont importés depuis `assets/logo_lio.png` et `assets/train.jpeg`. Les pictogrammes de navigation et du parcours utilisent des SVG intégrés pour éviter les caractères manquants selon les polices du navigateur. Les vignettes restent les dégradés du design, sans photos inventées.

Le microphone utilise `MediaRecorder` puis `/api/analyzeVoice` (Whisper et LLM locaux). HTTPS ou localhost et l’autorisation du navigateur sont nécessaires. La transcription reste modifiable avant envoi au chat. Les modèles et dépendances audio doivent être installés côté backend ; le chat écrit et le formulaire restent utilisables indépendamment.

## Données et limites

La recherche actualisée renvoie une erreur explicite : aucune source opérationnelle n’est connectée. La case de démonstration permet de consulter une journée historique de desserte. Dates de circulation et autorisations groupes ne sont pas vérifiées, jauges et scores sont signalés comme simulés. Les distances des hébergements sont à vol d’oiseau et leurs gares provisoires. La durée demandée ne filtre pas les suggestions faute de source fiable. Une demande ne déclenche aucun email et n’est pas envoyée à SNCF liO.

## Vérification navigateur

Démarrer un backend avec les 57 hébergements importés et le serveur Vite, puis :

```bash
npx playwright install chromium
npm run test:e2e
```

Les tests utilisent l’API réelle, sans mock HTTP, sur 1440 px et 390 px. Ils écrivent uniquement des sessions/demandes/avis de test : utiliser une base SQLite dédiée, par exemple `DATABASE_URL=sqlite:////tmp/lio-e2e.db`. `E2E_BASE_URL` permet de changer l’adresse du frontend. Les captures de vérification sont produites dans `/tmp/lio-home-desktop.png`, `/tmp/lio-home-mobile.png` et les fichiers `lio-summary-*`.

Les conventions Vite suivent sa [documentation officielle](https://vite.dev/guide/).
