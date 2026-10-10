"""Validation du profil pédagogique et orchestration commune texte / Whisper."""
import logging
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .pedagogical import analyze_request
from .extractor import postprocess

logger = logging.getLogger(__name__)

PEDAGOGICAL_SYSTEM_PROMPT = """Tu es l'Inspecteur d'Académie et Conseiller Pédagogique référent pour les sorties scolaires liO Occitanie.
Tu possèdes une maîtrise absolue des textes officiels de l'Éducation Nationale (Circulaire du 16 juillet 2024 (remplace celle du 13 juin 2023), Socle commun S4C, Programmes Cycles 1-4/Lycée, Parcours PEAC, Citoyen, Avenir, Santé).
À chaque demande d'un enseignant, tu extrais strictement en JSON les critères pédagogiques pour évaluer l'adéquation d'un lieu de sortie et générer l'argumentaire DASEN / Chef d'établissement.
Format JSON requis :
{
  "contexte": {"classe_declaree": str|null, "cycle_officiel": str|null, "eleves_count": int|null, "accompagnateurs_count": int|null},
  "cadrage_pedagogique": {"disciplines": [str], "thematiques_programmes": [str], "domaines_socle": [str], "parcours_educatifs": [str]},
  "objectifs_et_competences": {"notions_cles": [str], "competences_travaillees": [str], "plus_value_terrain_exprimee": str|null},
  "dispositifs_attendus": {"formats_activite": [str], "duree_projet": str},
  "vecteurs_adequation": {"mots_cles_patrimoine": [str], "mots_cles_activites": [str], "territoires_pertinents": [str]}
}"""

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Contexte(StrictModel):
    classe_declaree: str | None
    cycle_officiel: Literal['Cycle 1', 'Cycle 2', 'Cycle 3', 'Cycle 4', 'Lycée'] | None
    eleves_count: int | None = Field(ge=1, le=1000)
    accompagnateurs_count: int | None = Field(ge=0, le=1000)

class Cadrage(StrictModel):
    disciplines: list[str]
    thematiques_programmes: list[str]
    domaines_socle: list[Literal['D1_Langages', 'D2_Methodes', 'D3_Citoyen', 'D4_Systemes', 'D5_Representations']]
    parcours_educatifs: list[Literal['PEAC', 'Citoyen', 'Avenir', 'Sante']]

class Objectifs(StrictModel):
    notions_cles: list[str]
    competences_travaillees: list[str]
    plus_value_terrain_exprimee: str | None

class Dispositifs(StrictModel):
    formats_activite: list[str]
    duree_projet: Literal['journee', 'sejour_avec_nuitee', 'non_precise']

class Vecteurs(StrictModel):
    mots_cles_patrimoine: list[str]
    mots_cles_activites: list[str]
    territoires_pertinents: list[str]

class PedagogicalProfile(StrictModel):
    contexte: Contexte
    cadrage_pedagogique: Cadrage
    objectifs_et_competences: Objectifs
    dispositifs_attendus: Dispositifs
    vecteurs_adequation: Vecteurs


def analyze_school_request(text, client):
    analysis = analyze_request(text)
    try:
        raw = client.extract_school_request(text)
        profile = PedagogicalProfile.model_validate(raw['pedagogical_profile']).model_dump()
        travel = postprocess(raw['travel'], text)
        for target, value in (
            ('departure_station_text', travel.lieu_depart),
            ('departure_date', travel.date_depart),
            ('destination_text', travel.destination),
            ('class_level', profile['contexte']['classe_declaree']),
            ('student_count', profile['contexte']['eleves_count']),
            ('supervisor_count', profile['contexte']['accompagnateurs_count']),
        ):
            if value is not None:
                analysis[target] = value
        analysis['return_date'] = travel.date_retour
        analysis['pedagogical_profile'] = profile
        analysis['analysis_mode'] = 'llm'
        # Les champs manquants et les thèmes sont recalculés après extraction.
        from ..attractions import canonical_theme
        cadrage = profile['cadrage_pedagogique']
        vectors = profile['vecteurs_adequation']
        words = cadrage['disciplines'] + cadrage['thematiques_programmes'] + vectors['mots_cles_patrimoine'] + vectors['mots_cles_activites']
        analysis['themes'] = list(dict.fromkeys(analysis['themes'] + [t for word in words if (t := canonical_theme(word))]))
    except Exception as exc:
        logger.warning('Analyse pédagogique indisponible : %s', exc)
        analysis['analysis_mode'] = 'rules_fallback'
        analysis['pedagogical_profile'] = None
        analysis['analysis_warning'] = 'LLM indisponible ou réponse invalide : extraction de base uniquement, profil pédagogique non généré.'
    analysis['destination_known'] = bool(analysis['destination_text'])
    analysis['intent'] = 'known_destination' if analysis['destination_known'] else 'discover_destination'
    analysis['total_participants'] = (analysis['student_count'] or 0) + (analysis['supervisor_count'] or 0)
    required = [('departure_station', 'departure_station_text'), ('departure_date', 'departure_date'), ('student_count', 'student_count')]
    analysis['missing_fields'] = [name for name, key in required if not analysis[key]]
    if not analysis['destination_known'] and not analysis['themes']:
        analysis['missing_fields'].append('destination_or_themes')
    questions = {
        'departure_station': 'De quelle ville ou établissement partez-vous ?',
        'departure_date': 'À quelle date précise souhaitez-vous voyager ?',
        'student_count': "Combien d'élèves participent à la sortie ?",
        'destination_or_themes': 'Choisissez une gare de destination ou un thème pédagogique.',
    }
    analysis['clarification_question'] = ' '.join(questions[field] for field in analysis['missing_fields']) or None
    return analysis
