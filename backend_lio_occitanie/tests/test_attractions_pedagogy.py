"""Recherche de visites et propagation texte/Whisper jusqu'au LLM."""
import json
from copy import deepcopy
import pytest
from test_frontend_contract import client, create, PROJECT
from app.llm.client import LLMClient
from app.llm.school import PEDAGOGICAL_SYSTEM_PROMPT, analyze_school_request

PROFILE = {
    'contexte': {'classe_declaree': '5e', 'cycle_officiel': 'Cycle 4', 'eleves_count': 25, 'accompagnateurs_count': 3},
    'cadrage_pedagogique': {'disciplines': ['Histoire'], 'thematiques_programmes': ['Moyen Âge'], 'domaines_socle': ['D2_Methodes', 'D5_Representations'], 'parcours_educatifs': ['PEAC']},
    'objectifs_et_competences': {'notions_cles': ['Architecture défensive'], 'competences_travaillees': ['Observer un monument'], 'plus_value_terrain_exprimee': None},
    'dispositifs_attendus': {'formats_activite': ['Carnet d’enquête'], 'duree_projet': 'journee'},
    'vecteurs_adequation': {'mots_cles_patrimoine': ['Château'], 'mots_cles_activites': ['Observation'], 'territoires_pertinents': []},
}
RAW = {'travel': {'nombre_personnes': 28, 'date_depart': '2026-11-15', 'date_retour': None, 'lieu_depart': 'Toulouse', 'destination': None}, 'pedagogical_profile': PROFILE}
TEXT = 'Sortie en 5e sur le Moyen Âge, depuis Toulouse le 2026-11-15 pour 25 élèves et 3 accompagnateurs.'


def test_station_search_ignores_theme_and_excludes_accommodations(client):
    http, _ = client
    data = http.post('/api/destinations/search', json={'destination_station': 'Nîmes', 'themes': ['nature']}).json()
    assert data['search_mode'] == 'station'
    assert {item['id'] for item in data['destinations']} == {'arenes-nimes', 'maison-carree'}
    assert all(item['kind'] == 'attraction' for item in data['destinations'])
    assert 'pont-du-gard' not in {item['id'] for item in data['destinations']}


def test_unknown_destination_requires_exactly_one_theme(client):
    http, _ = client
    for themes in ([], ['nature', 'patrimoine']):
        assert http.post('/api/destinations/search', json={'themes': themes}).status_code == 422
    data = http.post('/api/destinations/search', json={'themes': ['sciences']}).json()
    assert data['destinations']
    assert all('sciences' in item['theme_tags'] for item in data['destinations'])
    assert 'cite-carcassonne' not in {item['id'] for item in data['destinations']}


def test_explicit_theme_mode_overrides_old_known_session(client):
    http, _ = client
    identifier = create(http)
    http.patch(f'/api/v1/sessions/{identifier}', json=PROJECT)
    data = http.post('/api/destinations/search', json={'session_id': identifier, 'search_mode': 'theme', 'themes': ['nature']}).json()
    assert data['search_mode'] == 'theme'
    assert all('nature' in item['theme_tags'] for item in data['destinations'])


def test_every_llm_request_contains_system_prompt_and_user_text(monkeypatch):
    captured = []
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices': [{'message': {'content': json.dumps(RAW)}}]}
    class HTTP:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            captured.append(json)
            return Response()
    monkeypatch.setattr('app.llm.client.httpx.Client', HTTP)
    client = LLMClient()
    for text in (TEXT, 'Transcription exacte Whisper'):
        client.extract_school_request(text)
        payload = captured[-1]
        assert PEDAGOGICAL_SYSTEM_PROMPT in payload['messages'][0]['content']
        assert payload['messages'][-1] == {'role': 'user', 'content': text}
        schema = payload['response_format']['json_schema']['schema']
        assert 'Contexte' in schema['$defs']
        assert payload['max_tokens'] >= 1536


def test_text_and_whisper_use_same_pedagogy_and_profile_is_persisted(client, monkeypatch):
    http, _ = client
    calls = []
    def extraction(text):
        calls.append(text)
        return deepcopy(RAW)
    monkeypatch.setattr('app.main.llm_client.extract_school_request', extraction)
    monkeypatch.setattr('app.main.transcribe_audio_bytes', lambda *args, **kwargs: TEXT)
    audio = http.post('/api/analyzeVoice', files={'file': ('voice.wav', b'audio', 'audio/wav')}).json()
    assert audio['transcription'] == TEXT
    assert audio['pedagogical_profile'] == PROFILE
    text = http.post('/api/trips/analyze', json={'content': TEXT, 'input_mode': 'speech_to_text'}).json()
    assert calls == [TEXT, TEXT]
    assert text['extracted_data']['pedagogical_profile'] == PROFILE
    identifier = text['session_id']
    saved = http.get(f'/api/v1/sessions/{identifier}').json()
    assert saved['project']['pedagogical_profile'] == PROFILE
    project = {**PROJECT, 'class_level': '5e'}
    assert http.patch(f'/api/v1/sessions/{identifier}', json=project).status_code == 200
    saved = http.get(f'/api/v1/sessions/{identifier}').json()
    assert saved['project']['pedagogical_profile'] == PROFILE


def test_invalid_llm_json_is_not_presented_as_pedagogical_analysis():
    class InvalidLLM:
        def extract_school_request(self, text): return {'travel': {}, 'pedagogical_profile': {'contexte': {}}}
    data = analyze_school_request(TEXT, InvalidLLM())
    assert data['analysis_mode'] == 'rules_fallback'
    assert data['pedagogical_profile'] is None
    assert data['analysis_warning']
    assert data['student_count'] == 25


def test_empty_whisper_output_does_not_call_llm(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr('app.main.transcribe_audio_bytes', lambda *args, **kwargs: '')
    def unexpected(text): raise AssertionError('Pas de LLM sans parole détectée')
    monkeypatch.setattr('app.main.llm_client.extract_school_request', unexpected)
    data = http.post('/api/analyzeVoice', files={'file': ('voice.wav', b'audio', 'audio/wav')}).json()
    assert data['speech_detected'] is False


def test_radius_uses_coordinates_not_commune_or_theme(client):
    http, _ = client
    narrow = http.post('/api/destinations/search', json={'destination_station': 'Carcassonne', 'radius_km': 0.1}).json()
    assert narrow['destinations'] == []
    wider = http.post('/api/destinations/search', json={'destination_station': 'Carcassonne', 'radius_km': 5}).json()
    assert {'cite-carcassonne', 'chateau-comtal'} <= {item['id'] for item in wider['destinations']}
    assert all(0 < item['distance_vol_oiseau_km'] <= 5 for item in wider['destinations'])
    assert http.post('/api/destinations/search', json={'destination_station': 'Gare inventée'}).status_code == 422


def test_station_directory_has_coordinates_and_attribution(client):
    http, _ = client
    result = http.get('/api/stations').json()
    assert result['license'] == 'ODbL'
    assert any(station['name'] == 'Carcassonne' for station in result['stations'])
    assert all(station['latitude'] and station['longitude'] and station['source_url'] for station in result['stations'])


def test_official_station_spelling_keeps_historical_train_lookup():
    from app.train_engine import find_train_options
    reference = find_train_options('Toulouse', 'Montpellier', 22)
    actual = find_train_options('Toulouse-Matabiau', 'Montpellier-St-Roch', 22)
    assert reference
    assert [train['train_number'] for train in actual] == [train['train_number'] for train in reference]
