"""Adéquation pédagogique contextualisée et marche calculée sur réseau piéton."""
from copy import deepcopy
import httpx
import pytest
from test_frontend_contract import client, create, PROJECT
from test_attractions_pedagogy import PROFILE
from app.attractions import attraction_by_id
from app.visit_pedagogy import evaluate_visit
from app import walking


def test_score_depends_on_actual_project_and_explains_missing_criteria():
    site = attraction_by_id('chateau-comtal')
    partial = evaluate_visit(site, {'themes': ['patrimoine'], 'class_level': '5e'})
    complete = evaluate_visit(site, {'themes': ['patrimoine'], 'class_level': '5e', 'pedagogical_profile': PROFILE})
    mismatch = evaluate_visit(site, {'themes': ['nature']})
    assert partial['score'] == partial['coverage'] == 50
    assert partial['status'] == 'theme_only'
    assert complete['score'] > partial['score'] > mismatch['score']
    assert complete['score'] == sum(part['points'] for part in complete['components'])
    assert '5e' in complete['pedagogical_justification']
    assert 'Château Comtal' in complete['regulatory_argument']
    assert '16 juillet 2024' in complete['regulatory_argument']
    assert 'Domaine 5' in complete['regulatory_argument']
    assert all(reference['url'].startswith('https://www.education.gouv.fr/') for reference in complete['references'])


def test_unknown_project_is_not_given_invented_score():
    assert evaluate_visit(attraction_by_id('chateau-comtal'), {})['score'] is None


def test_high_school_does_not_claim_socle_validation():
    profile = deepcopy(PROFILE)
    profile['contexte']['cycle_officiel'] = 'Lycée'
    result = evaluate_visit(attraction_by_id('chateau-comtal'), {'themes': ['patrimoine'], 'class_level': 'seconde', 'pedagogical_profile': profile})
    assert 'Domaine 5' not in result['regulatory_argument']


def test_search_returns_assessment_but_keeps_station_mode_unfiltered(client):
    http, _ = client
    identifier = create(http)
    http.patch(f'/api/v1/sessions/{identifier}', json=PROJECT)
    data = http.post('/api/destinations/search', json={'session_id': identifier, 'destination_station': 'Nîmes', 'themes': ['nature'], 'class_level': '5e'}).json()
    assert len(data['destinations']) == 2
    assert all(site['pedagogical_assessment']['score'] == 0 for site in data['destinations'])
    assert all(site['pedagogical_assessment']['regulatory_argument'] and site['closest_station'] for site in data['destinations'])


@pytest.fixture
def uncached_walking(monkeypatch):
    monkeypatch.setattr(walking, '_cache', {})
    monkeypatch.setattr(walking, '_loaded', True)
    monkeypatch.setattr(walking, 'reserve_request', lambda: None)


def test_walking_uses_ign_pedestrian_profile_and_minutes(uncached_walking, monkeypatch):
    item = attraction_by_id('chateau-comtal')
    station = walking.closest_station(item)
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={'profile': 'pedestrian', 'timeUnit': 'minute', 'distanceUnit': 'meter',
            'duration': 36.2, 'distance': 2300, 'resourceVersion': 'test',
            'start': f"{station['longitude']},{station['latitude']}", 'end': f"{item['longitude']},{item['latitude']}"})
    factory = httpx.Client
    monkeypatch.setattr(walking.httpx, 'Client', lambda **kwargs: factory(transport=httpx.MockTransport(respond)))
    first = walking.walking_route(item)
    second = walking.walking_route(item)
    assert first == second
    assert len(requests) == 1
    assert requests[0].url.params['profile'] == 'pedestrian'
    assert requests[0].url.params['timeUnit'] == 'minute'
    assert first['estimated_walking_minutes'] == 37
    assert first['walking_distance_m'] == 2300
    assert first['closest_station'] == 'Carcassonne'


def test_missing_coordinates_do_not_call_routing(uncached_walking, monkeypatch):
    def unexpected(**kwargs): raise AssertionError('Pas de réseau sans coordonnées')
    monkeypatch.setattr(walking.httpx, 'Client', unexpected)
    assert walking.walking_route({'latitude': None, 'longitude': None})['estimated_walking_minutes'] is None


@pytest.mark.parametrize('invalid', ['network', 'car', 'negative', 'bad_snap'])
def test_routing_failure_never_converts_straight_line_to_minutes(uncached_walking, monkeypatch, invalid):
    item = attraction_by_id('chateau-comtal')
    station = walking.closest_station(item)
    def respond(request):
        if invalid == 'network': return httpx.Response(503)
        return httpx.Response(200, json={'profile': 'car' if invalid == 'car' else 'pedestrian', 'timeUnit': 'minute', 'distanceUnit': 'meter',
            'duration': -3 if invalid == 'negative' else 20, 'distance': 1000,
            'start': '0,0' if invalid == 'bad_snap' else f"{station['longitude']},{station['latitude']}",
            'end': f"{item['longitude']},{item['latitude']}"})
    factory = httpx.Client
    monkeypatch.setattr(walking.httpx, 'Client', lambda **kwargs: factory(transport=httpx.MockTransport(respond)))
    result = walking.walking_route(item)
    assert result['status'] == 'unavailable'
    assert result['estimated_walking_minutes'] is None


def test_walking_endpoint_uses_recorded_real_route(client):
    http, _ = client
    result = http.get('/api/destinations/chateau-comtal/walking').json()
    assert result['status'] == 'calculated'
    assert result['closest_station'] == 'Carcassonne'
    assert result['estimated_walking_minutes'] > 0
    assert result['walking_distance_m'] > 0
    assert result['calculated_at']
    missing = http.get('/api/destinations/cordes/walking').json()
    assert missing['status'] == 'missing_coordinates'
    assert missing['estimated_walking_minutes'] is None
    assert http.get('/api/destinations/does-not-exist/walking').status_code == 404
