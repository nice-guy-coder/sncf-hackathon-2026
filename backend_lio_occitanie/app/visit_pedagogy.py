"""Adéquation explicable : rapprochement éditorial, pas une certification des programmes."""
import re
from .attractions import canonical_theme, normalize

CIRCULAR_URL = 'https://www.education.gouv.fr/bo/2024/Hebdo30/MENE2407159C'
SOCLE_URL = 'https://www.education.gouv.fr/le-socle-commun-de-connaissances-de-competences-et-de-culture-12512'
# Pistes de travail proposées à partir des thèmes ; ne décrit pas des ateliers réservables.
OPPORTUNITIES = {
    'patrimoine': (['Histoire', 'Géographie'], ['D2_Methodes', 'D5_Representations'], ['PEAC'], 'un carnet d’enquête sur le patrimoine et des croquis commentés'),
    'nature': (['SVT', 'Géographie'], ['D2_Methodes', 'D4_Systemes'], ['Citoyen'], 'un relevé d’observations sur les paysages et la biodiversité'),
    'sciences': (['SVT', 'Physique-Chimie', 'Technologie'], ['D2_Methodes', 'D4_Systemes'], ['Avenir'], 'un carnet d’observation et une comparaison des phénomènes ou des techniques'),
    'art et culture': (['Arts Plastiques', 'Français/Lettres', 'Histoire'], ['D1_Langages', 'D5_Representations'], ['PEAC'], 'une lecture des œuvres et une restitution orale ou artistique'),
    'mer et littoral': (['SVT', 'Géographie'], ['D2_Methodes', 'D4_Systemes'], ['Citoyen'], 'une enquête sur les milieux littoraux et leur préservation'),
    'sport': (['EPS', 'Géographie'], ['D2_Methodes', 'D3_Citoyen'], ['Sante'], 'une lecture de paysage et une activité collective adaptée au groupe'),
}
DOMAIN_LABELS = {
    'D1_Langages': 'Domaine 1 — les langages', 'D2_Methodes': 'Domaine 2 — les méthodes et outils pour apprendre',
    'D3_Citoyen': 'Domaine 3 — la formation de la personne et du citoyen',
    'D4_Systemes': 'Domaine 4 — les systèmes naturels et techniques',
    'D5_Representations': 'Domaine 5 — les représentations du monde et l’activité humaine',
}
STOPWORDS = {'avec', 'pour', 'dans', 'sortie', 'scolaire', 'eleves', 'classe', 'observer', 'observation', 'travailler'}


def overlap(expected, available):
    requested = {normalize(value) for value in expected}
    supported = {normalize(value) for value in available}
    # Discipline « Français » et « Français/Lettres » : même piste de travail.
    requested = {'francais lettres' if value == 'francais' else value for value in requested}
    return len(requested & supported) / len(requested) if requested else 0


def evaluate_visit(item, project):
    profile = project.get('pedagogical_profile') or {}
    cadrage = profile.get('cadrage_pedagogique', {})
    objectives = profile.get('objectifs_et_competences', {})
    vectors = profile.get('vecteurs_adequation', {})
    tags = item['theme_tags']
    opportunities = [OPPORTUNITIES[tag] for tag in tags if tag in OPPORTUNITIES]
    disciplines = sorted({word for entry in opportunities for word in entry[0]})
    domains = sorted({word for entry in opportunities for word in entry[1]})
    pathways = sorted({word for entry in opportunities for word in entry[2]})
    requested_themes = {canonical_theme(theme) for theme in project.get('themes', [])} - {None}
    if not requested_themes:
        requested_themes = {canonical_theme(word) for word in cadrage.get('thematiques_programmes', [])} - {None}
    theme_match = bool(requested_themes & set(tags))
    keywords = objectives.get('notions_cles', []) + vectors.get('mots_cles_patrimoine', []) + vectors.get('mots_cles_activites', [])
    keyword_tokens = {token for value in keywords for token in normalize(value).split() if len(token) >= 4 and token not in STOPWORDS}
    site_text = normalize(' '.join([item['name'], item['description'], *tags]))
    hits = sorted(token for token in keyword_tokens if re.search(r'\b' + re.escape(token) + r'\w*\b', site_text))
    components = [
        {'label': 'Thème du projet', 'points': 50 if theme_match else 0, 'maximum': 50, 'renseigné': bool(requested_themes)},
        {'label': 'Disciplines', 'points': round(20 * overlap(cadrage.get('disciplines', []), disciplines)), 'maximum': 20, 'renseigné': bool(cadrage.get('disciplines'))},
        {'label': 'Domaines du socle', 'points': round(15 * overlap(cadrage.get('domaines_socle', []), domains)), 'maximum': 15, 'renseigné': bool(cadrage.get('domaines_socle'))},
        {'label': 'Notions et mots-clés du projet', 'points': round(15 * len(hits) / len(keyword_tokens)) if keyword_tokens else 0, 'maximum': 15, 'renseigné': bool(keyword_tokens)},
    ]
    coverage = sum(component['maximum'] for component in components if component['renseigné'])
    score = sum(component['points'] for component in components) if coverage else None
    classroom = project.get('class_level') or profile.get('contexte', {}).get('classe_declaree')
    cycle = profile.get('contexte', {}).get('cycle_officiel')
    group = f"pour la classe de {classroom}" if classroom else "pour le groupe scolaire"
    topic = ', '.join(sorted(requested_themes)) or 'le thème à préciser'
    relation = f"Le lieu correspond au thème « {topic} »" if theme_match else f"Le lien avec le thème « {topic} » doit être précisé"
    activity = opportunities[0][3] if opportunities else 'un carnet d’observation et une restitution collective'
    justification = f"{item['name']} : {item['description']} {relation} {group}. Une piste de travail serait {activity}."
    if hits:
        justification += ' Notions repérées dans le descriptif : ' + ', '.join(hits) + '.'
    matched_domains = set(cadrage.get('domaines_socle', [])) & set(domains)
    domains_to_propose = sorted(matched_domains or set(domains))
    socle = ''
    if cycle != 'Lycée' and (not classroom or not any(value in normalize(classroom) for value in ['lycee', 'seconde', 'premiere', 'terminale', 'bts', 'cap', '2nde'])):
        socle = ' Le projet peut travailler ' + ', '.join(DOMAIN_LABELS[domain] for domain in domains_to_propose) + ', selon les objectifs retenus par l’enseignant.'
    opening = (f"La visite de {item['name']} {group} constitue un support concret pour aborder {topic}. "
               if theme_match else f"Pour retenir la visite de {item['name']} {group}, le dossier devra préciser son lien avec {topic}. ")
    argument = (
        opening +
        f"Le travail proposé porte sur : {item['description']} "
        "En cohérence avec la circulaire du 16 juillet 2024, le dossier doit expliciter son articulation avec les enseignements et le projet de la classe. "
        f"La proposition comprend une préparation en classe, puis {activity} sur place, et une restitution évaluée au retour."
        + socle +
        ' Les modalités d’encadrement, de sécurité, d’inclusion et les autorisations restent à préciser dans le dossier de sortie.'
    )
    return {
        'score': score, 'maximum': 100, 'coverage': coverage, 'components': components,
        'status': 'profile' if profile else ('theme_only' if coverage else 'needs_project'),
        'notice': 'Score indicatif fondé sur les critères renseignés. Les critères manquants ne sont pas évalués ; aucun programme ni accueil scolaire n’est certifié.',
        'pedagogical_justification': justification, 'regulatory_argument': argument,
        'proposed_disciplines': disciplines, 'proposed_domains': domains_to_propose, 'proposed_pathways': pathways,
        'references': [{'title': 'Circulaire du 16 juillet 2024', 'url': CIRCULAR_URL}, {'title': 'Socle commun', 'url': SOCLE_URL}],
    }
