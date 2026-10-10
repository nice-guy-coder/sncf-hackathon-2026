"""Analyse pédagogique et ferroviaire spécifique aux sorties scolaires liO Occitanie."""
import re

THEMES = {
    "patrimoine": [
        "patrimoine", "histoire", "historique", "monument", "moyen âge", "moyen-âge",
        "moyen age", "château", "chateau", "cathare", "cité", "cite", "romain", "archéologie"
    ],
    "nature": [
        "nature", "environnement", "biodiversité", "biodiversite", "forêt", "foret",
        "montagne", "parc", "écologie", "ecologie", "pyrénées", "pyrenees", "grotte"
    ],
    "sciences": [
        "science", "scientifique", "astronomie", "espace", "technologie", "physique", "muséum"
    ],
    "art et culture": [
        "art", "culture", "musée", "musee", "peinture", "théâtre", "theatre", "sculpture"
    ],
    "mer et littoral": [
        "mer", "littoral", "plage", "méditerranée", "mediterranee", "côte", "cote", "maritime"
    ],
    "sport": [
        "sport", "randonnée", "randonnee", "escalade", "vélo", "velo", "plein air"
    ]
}

KNOWN_CITIES = [
    "toulouse", "montpellier", "carcassonne", "nîmes", "nimes", "albi", "foix",
    "perpignan", "béziers", "beziers", "narbonne", "rodez", "tarbes", "lourdes",
    "castelnaudary", "cahors", "auch", "montauban", "agde", "sete", "sète"
]


def analyze_request(text: str) -> dict:
    low = text.lower()
    result = {
        "intent": "discover_destination",
        "departure_station_text": None,
        "departure_date": None,
        "class_level": None,
        "student_count": None,
        "supervisor_count": None,
        "total_participants": None,
        "destination_text": None,
        "destination_known": False,
        "themes": [],
        "max_train_minutes": None,
        "missing_fields": [],
        "clarification_question": None,
        "analysis_mode": "rules_and_nlp"
    }

    # 1. Thèmes pédagogiques
    for theme, keywords in THEMES.items():
        if any(w in low for w in keywords):
            result["themes"].append(theme)

    # 2. Niveau de classe
    m_class = re.search(r"\b(classe de\s+)?(\d{1,2}(?:e|ème|eme)|cm1|cm2|ce1|ce2|cp|seconde|première|terminale|collège|lycée)\b", low)
    if m_class:
        result["class_level"] = m_class.group(2).strip()

    # 3. Nombre d'élèves
    m_students = re.search(r"\b(\d{1,3})\s+(?:élèves|eleves|élève|eleve|enfants)\b", low)
    if m_students:
        result["student_count"] = int(m_students.group(1))

    # 4. Nombre d'accompagnateurs
    m_sup = re.search(r"\b(\d{1,2})\s+(?:accompagnateurs|accompagnateur|adultes|encadrants|profs|professeurs)\b", low)
    if m_sup:
        result["supervisor_count"] = int(m_sup.group(1))

    # Total participants
    students = result["student_count"] or 0
    supervisors = result["supervisor_count"] or 0
    if students or supervisors:
        result["total_participants"] = students + supervisors

    # 5. Date
    m_date = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if m_date:
        result["departure_date"] = m_date.group(1)
    else:
        m_date_fr = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})\b", text)
        if m_date_fr:
            result["departure_date"] = f"{m_date_fr.group(3)}-{int(m_date_fr.group(2)):02d}-{int(m_date_fr.group(1)):02d}"

    # 6. Gare ou ville de départ
    m_dep = re.search(r"(?:au départ de|depart de|depuis|partons du collège de|partons du lycée de|partons de|partant de|gare de)\s+([A-Za-zÀ-ÿ' -]{2,60})", text, re.I)
    if m_dep:
        raw_dep = re.split(r",|\.|\s+le\s+|\s+pour\s+|\s+avec\s+|\s+en\s+", m_dep.group(1), flags=re.I)[0].strip()
        cleaned_dep = re.sub(r"^(?:collège de|college de|lycée de|lycee de|gare de|gare d')\s*", "", raw_dep, flags=re.I).strip()
        if cleaned_dep:
            result["departure_station_text"] = cleaned_dep.capitalize()

    if not result["departure_station_text"]:
        for city in KNOWN_CITIES:
            if re.search(rf"\b(à|a|de)\s+{city}\b", low):
                result["departure_station_text"] = city.capitalize()
                break

    # 7. Destination
    m_dest = re.search(r"(?:destination|visiter|aller à|aller a|à destination de|vers)\s+([A-Za-zÀ-ÿ' -]{2,60})", text, re.I)
    if m_dest:
        raw_dest = re.split(r",|\.|\s+le\s+|\s+pour\s+|\s+avec\s+|\s+en\s+", m_dest.group(1), flags=re.I)[0].strip()
        cleaned_dest = re.sub(r"^(?:la ville de|la gare de)\s*", "", raw_dest, flags=re.I).strip()
        if cleaned_dest and cleaned_dest.lower() != (result["departure_station_text"] or "").lower():
            result["destination_text"] = cleaned_dest.capitalize()
            result["destination_known"] = True
            result["intent"] = "known_destination"

    # 8. Contrainte de temps de train max
    m_max = re.search(r"(?:moins de|maximum|max\.?)\s+(\d{1,3})\s*(?:minutes|min|h|heures)", low)
    if m_max:
        val = int(m_max.group(1))
        if "h" in m_max.group(0):
            val *= 60
        result["max_train_minutes"] = val

    # 9. Champs manquants
    if not result["departure_station_text"]:
        result["missing_fields"].append("departure_station")
    if not result["departure_date"]:
        result["missing_fields"].append("departure_date")
    if not result["student_count"]:
        result["missing_fields"].append("student_count")
    if not result["destination_known"] and not result["themes"] and result["max_train_minutes"] is None:
        result["missing_fields"].append("destination_or_themes")

    if result["missing_fields"]:
        questions = []
        if "departure_station" in result["missing_fields"]:
            questions.append("De quelle ville ou établissement partez-vous ?")
        if "student_count" in result["missing_fields"]:
            questions.append("Combien d'élèves participent à la sortie ?")
        if "departure_date" in result["missing_fields"]:
            questions.append("À quelle date précise souhaitez-vous voyager ?")
        if "destination_or_themes" in result["missing_fields"]:
            questions.append("Avez-vous une destination en tête ou un thème pédagogique (patrimoine, nature, sciences...) ?")
        result["clarification_question"] = " ".join(questions)

    return result
