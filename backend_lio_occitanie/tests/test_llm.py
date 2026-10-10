from app.llm import analyze_request
def test_extracts_station_date_theme():
    x=analyze_request("Sortie nature au départ de Toulouse le 2026-11-15.")
    assert x["departure_station_text"]=="Toulouse"
    assert x["departure_date"]=="2026-11-15"
    assert "nature" in x["themes"]
