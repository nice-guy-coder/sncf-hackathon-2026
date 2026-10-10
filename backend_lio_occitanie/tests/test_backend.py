import sys
from pathlib import Path

# Ajouter backend au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm import analyze_request, TravelExtractor, TravelInfo
from app.llm.extractor import extract_heuristic_fallback
from app.train_engine import find_train_options, calculate_confidence_score
from app.stt import get_model_path, MODELS_DIR

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
    assert score_ok["score"] >= 90

    score_bad = calculate_confidence_score(
        regularity_rate=70.0,
        cancellation_rate=20.0,
        walking_minutes=45,
        available_seats=20,
        requested_pax=35
    )
    assert score_bad["score"] < score_ok["score"]
    assert score_bad["details"]["capacity_pts"] == 0.0

def test_whisper_model_configuration():
    """Vérifie la configuration du modèle Whisper et le manifest HuggingFace."""
    model_p = get_model_path()
    assert "ggml" in model_p.name

    # Vérifier la présence du manifest
    manifest = MODELS_DIR / "manifest.json"
    assert manifest.exists()

    try:
        import numpy as np
        from app.stt import to_mono_16k
        dummy_stereo = np.random.randint(-32000, 32000, size=(44100, 2), dtype=np.int16)
        mono_16k = to_mono_16k(dummy_stereo, 44100)
        assert mono_16k.ndim == 1
        assert len(mono_16k) == 16000
    except ImportError:
        pass # Numpy sera exécuté dans le conteneur Docker

def test_travel_extractor_mock():
    """Vérifie l'extraction via mock LLM et post-processing."""
    class MockLLM:
        def extract_raw(self, description: str):
            return {
                "nombre_personnes": 30,
                "date_depart": "2026-11-15",
                "date_arrivee": None,
                "lieu_depart": "Toulouse",
                "destination": "Carcassonne",
            }

    extractor = TravelExtractor(MockLLM())
    res = extractor.extract("Nous partons de Toulouse pour aller à Carcassonne le 2026-11-15 avec 30 élèves.")
    assert res.nombre_personnes == 30
    assert res.lieu_depart == "Toulouse"
    assert res.destination == "Carcassonne"
    assert res.destination_connue is True
    assert res.date_depart == "2026-11-15"

def test_travel_extractor_heuristic_fallback():
    """Vérifie que la bascule automatique sur l'heuristique fonctionne si le serveur LLM échoue."""
    class FailingLLM:
        def extract_raw(self, description: str):
            raise ConnectionError("Serveur llama.cpp injoignable")

    extractor = TravelExtractor(FailingLLM())
    res = extractor.extract("Nous sommes 40 élèves au départ de Foix pour aller à Carcassonne le 2026-11-15.")
    assert res.nombre_personnes == 40
    assert res.lieu_depart == "Foix"
    assert res.destination == "Carcassonne"
    assert res.destination_connue is True
    assert res.date_depart == "2026-11-15"

if __name__ == "__main__":
    test_analyze_request_cadrage_example()
    test_analyze_request_missing_info()
    test_train_engine_search_and_jauge()
    test_confidence_score_calculation()
    test_whisper_model_configuration()
    test_travel_extractor_mock()
    test_travel_extractor_heuristic_fallback()
    print("Tous les tests passent avec succès !")
