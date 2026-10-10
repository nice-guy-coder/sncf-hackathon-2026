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

Le navigateur obtient les attractions uniquement par `POST /api/destinations/search` et les trains par `POST /api/trains/search`. `src/api.ts` porte les requêtes HTTP ; `src/useDestinations.ts` charge le catalogue depuis l’API à l’ouverture de `#suggestions`, à son rechargement et lors des changements de filtre. Les réponses ne sont pas remplacées par un catalogue local si le backend est indisponible : une erreur et un bouton Réessayer apparaissent.

Les catalogues JSON des attractions et des gares sont gérés exclusivement par le backend. Le classeur d’hébergements et son API historique ne sont plus utilisés par React. Aucun catalogue n’est embarqué dans React ni enregistré dans le stockage du navigateur. Les noms de fichiers ne sont pas affichés dans les cartes/détails : l’interface présente les lieux et la date de mise à jour du catalogue.

La configuration habituelle cible le backend Docker sur le port 8000. Le serveur temporaire sur 8011 et le proxy de test de l’aperçu ont été arrêtés après validation ; ils ne sont pas nécessaires au lancement de l’application.

## Parcours

Accueil → choix du mode → chat écrit/vocal ou formulaire → confirmation du projet et de la gare → attractions autour d’une gare connue ou suggestions par un thème unique → détails → recherche aller/retour → sélection et comparaison visuelle → récapitulatif → coordonnées → demande locale en attente → retour d’expérience.

Les demandes et avis sont écrits dans la base backend. Le brouillon du projet est conservé dans le `sessionStorage` de l’onglet, sans coordonnées de contact. Les résultats doivent être recherchés à nouveau après rechargement. Les écrans utilisent les styles des 22 prototypes HTML ; les variantes mobiles sont appliquées par media queries. Le logo liO et la photo d’accueil sont importés depuis `assets/logo_lio.png` et `assets/train.jpeg`. Les pictogrammes de navigation et du parcours utilisent des SVG intégrés pour éviter les caractères manquants selon les polices du navigateur. Les vignettes restent les dégradés du design, sans photos inventées.

Le microphone utilise `MediaRecorder` puis `/api/analyzeVoice` (Whisper et LLM locaux). HTTPS ou localhost et l’autorisation du navigateur sont nécessaires. La transcription reste modifiable avant envoi au chat. Les modèles et dépendances audio doivent être installés côté backend ; le chat écrit et le formulaire restent utilisables indépendamment.

## Données et limites

La recherche actualisée renvoie une erreur explicite : aucune source opérationnelle n’est connectée. La case de démonstration permet de consulter une journée historique de desserte. Dates de circulation et autorisations groupes ne sont pas vérifiées, jauges et scores sont signalés comme simulés. Les distances des attractions géolocalisées sont calculées à vol d’oiseau depuis les coordonnées SNCF. Les lieux non géolocalisés sont exclus de la recherche par rayon ; leur gare de rattachement reste indicative dans les suggestions par thème. Les distances ne constituent pas un itinéraire piéton. Le filtre par temps de train a été retiré du parcours. Une demande ne déclenche aucun email et n’est pas envoyée à SNCF liO.

## Vérification navigateur

Démarrer un backend avec les catalogues JSON fournis et le serveur Vite, puis :

```bash
npx playwright install chromium
npm run test:e2e
```

Les tests utilisent l’API réelle, sans mock HTTP, sur 1440 px et 390 px. Ils écrivent uniquement des sessions/demandes/avis de test : utiliser une base SQLite dédiée, par exemple `DATABASE_URL=sqlite:////tmp/lio-e2e.db`. `E2E_BASE_URL` permet de changer l’adresse du frontend. Les captures de vérification sont produites dans `/tmp/lio-home-desktop.png`, `/tmp/lio-home-mobile.png` et les fichiers `lio-summary-*`.

Les conventions Vite suivent sa [documentation officielle](https://vite.dev/guide/).

## Recherche des attractions et analyse pédagogique

`GET /api/stations` alimente les suggestions de noms de gares. La recherche transmet `search_mode`, `destination_station`, `radius_km` et `themes`. Le mode `station` ignore les thèmes et trie les attractions par distance. Le mode `theme` exige exactement un thème et ne réutilise pas une ancienne destination de session.

Le chat et l’audio utilisent le même pré-prompt système et un JSON validé. La transcription Whisper reste le message utilisateur, séparé du pré-prompt système. Le profil pédagogique s’affiche sur la fiche d’attraction lorsque disponible. Les anciennes sélections d’hébergements du navigateur sont abandonnées via une nouvelle clé de brouillon.

## Informations sous chaque lieu

Les cartes et les fiches affichent le score, la justification pédagogique, l’argumentaire réglementaire (déplié par défaut) et les liens officiels. « Comprendre le score » détaille les points et les critères manquants. Une note fondée uniquement sur le thème est identifiée comme partielle.

Les minutes sont chargées séparément par `GET /api/destinations/{id}/walking` pour ne pas ralentir les résultats pédagogiques. La carte indique la gare la plus proche, la durée estimée, la distance sur l’itinéraire IGN et la date du calcul. Une erreur conserve la carte et propose de réessayer le calcul à pied. Les 9 lieux sans coordonnées n’ont pas de durée inventée.
