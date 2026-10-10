import sys
from pathlib import Path

# Ajouter backend au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm import analyze_request
from app.train_engine import find_train_options, calculate_confidence_score

def test_analyze_request_cadrage_example():
    """Teste l'exemple exact de la fiche de cadrage SNCF."""
    prompt = (
        "Je souhaite travailler avec ma classe de 5e sur le Moyen Âge. "
        "Nous sommes 42 élèves et 4 accompagnateurs. "
        "Nous souhaitons faire une sortie sur une journée, en train liO, avec un départ le matin et un retour avant 19h. "
        "Nous partons du collège de Foix le 2026-11-15."
    )
    res = analyze_request(prompt)

    assert res["class_level"] == "5e"
    assert res["student_count"] == 42
    assert res["supervisor_count"] == 4
    assert res["total_participants"] == 46
    assert res["departure_station_text"] == "Foix"
    assert res["departure_date"] == "2026-11-15"
    assert "patrimoine" in res["themes"]
    assert len(res["missing_fields"]) == 0

def test_analyze_request_missing_info():
    """Vérifie la génération de la question de clarification si des infos manquent."""
    prompt = "Sortie scolaire pour 25 élèves."
    res = analyze_request(prompt)
    assert res["student_count"] == 25
    assert "departure_station" in res["missing_fields"]
    assert "departure_date" in res["missing_fields"]
    assert res["clarification_question"] is not None

def test_train_engine_search_and_jauge():
    """Vérifie la recherche de trains liO réels et le contrôle de la jauge (50 pax)."""
    options = find_train_options(
        origin="Toulouse",
        destination_station="Carcassonne",
        requested_pax=35,
        walking_minutes=12
    )

    assert len(options) > 0
    first = options[0]

    # Vérification de la jauge
    gauge = first["group_capacity"]
    assert gauge["max_limit"] == 50
    assert gauge["available_seats"] >= 0
    assert "places disponibles" in gauge["message"]

    # Vérification de l'accessibilité <= 20 min
    assert first["accessibility_site"]["is_under_20_min"] is True

    # Vérification de l'Indicateur Confiance Voyageur Scolaire (/100)
    conf = first["confidence_indicator"]
    assert 10 <= conf["score"] <= 100
    assert "regularity_pts" in conf["details"]
    assert "reliability_pts" in conf["details"]
    assert len(conf["explanation"]) > 0

def test_confidence_score_calculation():
    """Vérifie le calcul transparent de l'indice de confiance."""
    score_ok = calculate_confidence_score(
        regularity_rate=90.0,
        cancellation_rate=3.0,
        walking_minutes=15, # <= 20 min
        available_seats=40,
        requested_pax=30
    )
    # 90% reg -> 36 pts, 97% non-supp -> 29.1 pts, access -> 15 pts, cap -> 15 pts => ~95
    assert score_ok["score"] >= 90

    # Cas avec capacité insuffisante et distance élevée
    score_bad = calculate_confidence_score(
        regularity_rate=70.0,
        cancellation_rate=20.0,
        walking_minutes=45,
        available_seats=20,
        requested_pax=35
    )
    assert score_bad["score"] < score_ok["score"]
    assert score_bad["details"]["capacity_pts"] == 0.0

if __name__ == "__main__":
    test_analyze_request_cadrage_example()
    test_analyze_request_missing_info()
    test_train_engine_search_and_jauge()
    test_confidence_score_calculation()
    print("Tous les tests passent avec succès !")
