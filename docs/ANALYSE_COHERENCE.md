# Analyse de cohérence — 10 octobre 2026

> Mise à jour du périmètre : le parcours utilise désormais des attractions touristiques autour d’une gare ou selon un thème unique si la destination est inconnue. Les décisions historiques ci-dessous relatives aux hébergements et à l’analyse par règles sont remplacées par le [contrat actuel](../backend_lio_occitanie/README.md#contrat-pédagogique-et-attractions). Le chat et Whisper sollicitent le LLM avec le pré-prompt de la synthèse pédagogique.

## Documents et données examinés

- Fiche de cadrage hackathon, 13 pages, y compris l’annexe tarifaire en images et le processus actuel de réservation.
- Pitch participants, 6 pages.
- Spécification backend DOCX et version PDF, 6 pages. Le DOCX copié dans le backend est identique à celui du dossier `Technical specs` (SHA-256 vérifié).
- Schémas « Frontend Workflow » et « Frontend and backend relation ».
- Les 22 prototypes HTML : 11 écrans/parcours, chacun en desktop et mobile. Les branches 06a/06b expliquent la numérotation en dix étapes.
- Code FastAPI, modèles SQLAlchemy, client LLM, extracteurs, Whisper, moteur ferroviaire, importeurs, scripts, tests, configuration Docker et frontend de test existant.
- CSV de régularité, classeur d’hébergements (onglets `Lire d’abord` et `Hebergements Occitanie`), desserte Excel (796 179 lignes de données), JSON ferroviaire dérivé et base SQLite fournie (57 structures).

## Décisions retenues

Les maquettes sont la référence visuelle demandée par l’utilisateur. Le cadrage et le pitch portent les objectifs métier. Les réserves de la spécification sur la qualité et la provenance des données doivent être conservées. Les divergences ne sont pas masquées.

| Sujet | Écart constaté | Décision et réalisation |
|---|---|---|
| Modes de saisie | La spécification interdit le formulaire ; les maquettes et le workflow le demandent. | Chat écrit, dictée et formulaire équivalents, suivant la demande de respecter les maquettes. Le formulaire crée une session structurée directement, sans dépendre d’un LLM. |
| Gare de départ | Le cadrage attend une identification à partir du lieu réel ; le schéma d’architecture et la spécification exigent une gare saisie par l’utilisateur. | Le lieu réel est conservé et une gare est explicitement confirmée par l’enseignant. Aucun géocodeur/GTFS complet n’étant connecté, aucune gare n’est présentée comme automatiquement vérifiée. |
| Date | Le cadrage autorise une période ; les spécifications et la recherche attendent une date précise. | Date précise pour aller et retour. Une date invalide déclenche une clarification ou une erreur de validation. |
| Catalogue | Les maquettes affichent des sites culturels ; les données décrivent des hébergements. | Cartes et détails utilisent exclusivement les 57 hébergements importés. Les « activités proches » restent un texte source, sans création de sites officiels. |
| Gares et distances | Le classeur indique que ses deux dernières colonnes sont provisoires et utilisent seulement 20 gares ; le backend convertissait la distance en marche. | Distance à vol d’oiseau et gare provisoire affichées explicitement. Aucune durée piétonne, aucun verdict PMR ou de faisabilité calculé depuis cette distance. |
| Seuil d’accès | L’onglet `Lire d’abord` mentionne 15 min ; cadrage et pitch indiquent 20 min. | Le seuil cible du projet est 20 min, mais aucun résultat n’est évalué contre ce seuil tant qu’un accès réel n’est pas disponible. |
| Données ferroviaires | La spécification a été rédigée avant l’ajout des fichiers SNCF ; le backend présente une journée historique comme applicable à toute date. | Recherche opérationnelle : 503 explicite. Recherche historique sur consentement explicite via `demo=true`, pour démontrer le parcours. |
| Autorisation groupes | Le générateur marque toutes les circulations comme autorisées. La liste opérationnelle d’autorisations n’est pas connectée. | Aucune autorisation réelle revendiquée. Les résultats restent des données de démonstration à vérifier. |
| Capacité | Le générateur invente les places sous option par un hash ; le pitch interdit les disponibilités inventées. | Jauge et disponibilité portent le libellé « simulée ». Le plafond métier de 50 est confirmé par le cadrage et validé dans le frontend et le backend. |
| Score de confiance | Le moteur combine des historiques, des moyennes de repli et des capacités/accès simulés. | Score de démonstration avec détail des composantes ; pas de garantie future. Les avis sont enregistrés mais ne modifient pas encore le score. |
| Aller/retour | Le backend ne fournissait qu’une recherche aller ; les maquettes ont un retour. | Deux recherches du même moteur, en sens inverse et avec les dates demandées, puis deux sélections persistées. Le retour d’une journée doit partir après l’arrivée aller. Les correspondances restent non implémentées. |
| Demande | Les maquettes parlent d’envoi SNCF et de réponse/email ; l’API ne fait qu’écrire dans SQLite. | Demande locale `pending`, référence de dossier et message explicite « aucun envoi SNCF ni email ». Aucune confirmation de billet. Le projet et les deux sélections sont conservés dans la demande. |
| Tarif | L’annexe donne un barème scolaire (6 à 50 personnes), un délai minimum de 21 jours et des conditions 9h–16h/cas particuliers. | Ces conditions sont documentées comme règles de l’offre fournie ; aucun prix ni éligibilité tarifaire actuelle n’est promis par l’application. À vérifier auprès du service liO. |
| Images | `hero-landscape.png` est référencé mais absent ; les autres vignettes sont déjà des dégradés. | Dégradés du prototype conservés. Aucune photographie ou destination inventée pour remplacer les sources manquantes. |

## Design et parcours réalisés

Tokens repris du CSS des prototypes : fond `#f3f1ef`, rose `#e3007c`, bleu `#0b2a4a`, surfaces blanches, bordures `#e3dee2`, Poppins pour les titres et Inter pour les textes. Largeur maximale 1440 px, contenu 1180 px, barre desktop 72 px. Sur mobile, barre 56 px, marges 20 px, titres 24 px, cartes empilées, boutons pleine largeur et menu burger.

Les exemples figés (Carcassonne, horaires, 46 places, date d’avril) deviennent des données API. Les ajouts nécessaires sont la confirmation de gare, la dictée, le consentement au mode historique, les sélections aller/retour, les messages d’erreur, la confirmation de demande, l’impression et quatre critères de retour d’expérience. Les fonctions de provenance et d’avertissement prolongent la charte des maquettes sans ajouter de nouvelle palette.

La représentation des horaires est une comparaison visuelle par cartes (durée, jauge et score explicable). Aucun moteur de correspondances ou classement pédagogique exhaustif n’est annoncé.

## Contrats frontend/backend

| Écran / action | Route utilisée | Résultat |
|---|---|---|
| Dictée | `POST /api/analyzeVoice` multipart `file`, `language=fr` | Transcription modifiable, détection de parole ; Whisper puis extracteur local. |
| Chat / précision | `POST /api/trips/analyze` | `session_id`, `extracted_data`, question et champs manquants. Les messages successifs sont conservés pour réanalyse ; les corrections d’effectifs prennent la dernière valeur. |
| Formulaire | `POST /api/v1/sessions`, `PATCH /api/v1/sessions/{id}` | Session structurée sans extraction heuristique du formulaire. |
| Lecture de session | `GET /api/v1/sessions/{id}` | Projet enregistré et sélections. |
| Suggestions / filtres | `POST /api/destinations/search` | Hébergements et provenance ; durée non appliquée explicitement. Les filtres visibles utilisent les thèmes effectivement présents. |
| Trains aller puis retour | `POST /api/trains/search` | 503 sans source ; `historical_demo` avec `demo=true`. Jauge/score simulés, accès inconnu. |
| Sélections | `PATCH /api/v1/sessions/{id}` | Validation de la liaison, de la jauge simulée et de la chronologie. Toute modification du trajet invalide les anciennes sélections. |
| Récapitulatif | `POST /api/trips/summary` | Projet réel et destination, aucun train par défaut inventé. |
| Demande | `POST /api/prereservations` | Référence, statut `pending`, copie du projet et de l’itinéraire dans la demande. |
| Avis | `POST /api/feedback` | Avis enregistré avec la session. L’alias versionné lie désormais correctement le paramètre d’URL à la session. |

Les routes historiques et les alias déjà existants restent présents. Le contrat de recherche exige maintenant une date valide et une activation explicite de la démonstration. Les consommateurs de l’ancien frontend de test doivent intégrer ces nouvelles contraintes. Le proxy Vite évite les erreurs d’origine en développement ; CORS est configurable pour un appel direct.

## Validation

- Compilation TypeScript et bundle Vite réussis. 19 tests backend et 10 parcours navigateur desktop/mobile passent sur la version livrée.
- Tests backend : suite existante et nouveaux tests de contrats sur SQLite isolée.
- Tests Playwright contre FastAPI réel : parcours connu aller/retour → résumé → demande → avis ; parcours inconnu → thème → détail ; chat → clarification → validation d’effectif → reprise du brouillon.
- Deux tailles vérifiées : desktop 1440 × 1000 et mobile 390 × 844 ; contrôle de l’absence de débordement horizontal aux étapes clés et captures visuelles examinées.
- Une régression préexistante dans le fallback vocal (`pour aller à Carcassonne` interprété comme lieu « Aller à carcassonne ») a été corrigée et couverte par le test existant.
- Les modèles LLM/Whisper réels n’ont pas été lancés dans cette validation. L’autorisation micro, la transcription effective et la qualité du modèle demandent un essai avec la stack audio configurée.
- Docker n’a pas été reconstruit. Les tests API et navigateur utilisent une base `/tmp` sans modifier les demandes de la base fournie.

## Suite du projet

Connecter les horaires datés, les autorisations groupes et les options/capacités opérationnelles est nécessaire pour passer de la démonstration à des propositions utilisables. Il faut aussi un référentiel complet de gares, des accès gare–site routés et un catalogue de visites validé pour automatiser le choix pédagogique et la faisabilité.

Le schéma cible de la spécification reste plus large que le prototype : conversations normalisées, tables d’itinéraires, imports traçables, authentification, suivi de demandes, connecteur officiel, notifications et agrégation des avis. Aucune de ces extensions n’est implicitement déclarée réalisée. Les données SNCF du cadrage sont réservées au hackathon : elles restent dans l’API locale et ne sont pas copiées dans le bundle frontend ni publiées.

## Correction de l’accès au catalogue

Le chargement de Suggestions est désormais déclenché par l’ouverture de la page, y compris via un lien direct ou un rechargement. Il appelle toujours `/api/destinations/search`, annule les requêtes devenues obsolètes et vide les anciens résultats lors d’une nouvelle recherche. Une panne affiche une erreur et permet une nouvelle tentative ; aucun fichier ou catalogue de secours n’est lu côté navigateur. Les références au classeur et aux noms de fichiers ont été remplacées dans l’interface par des libellés de catalogue et une date de mise à jour.

Les tests supplémentaires comparent les cartes à la réponse réelle de l’API, vérifient une nouvelle requête au rechargement, l’absence de requêtes CSV/XLSX et la reprise après une panne simulée du réseau. Le frontend habituel cible le backend sur 8000 ; l’aperçu temporaire sur 8011 a été arrêté après les tests.
