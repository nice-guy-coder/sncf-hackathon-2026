"""Contrats du parcours React : saisie structurée, données honnêtes, sélection, demande."""
import os
import sys
from pathlib import Path
os.environ.setdefault('DATABASE_URL', 'sqlite:////tmp/lio-contract-bootstrap.db')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import Base, get_db
from app.models import Accommodation, ReservationRequest, Feedback
from app.llm import analyze_request

@pytest.fixture
def client(monkeypatch):
    def offline(text):
        raise RuntimeError('LLM désactivé pour ces tests de contrat')
    monkeypatch.setattr('app.main.llm_client.extract_school_request', offline)
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Accommodation(id='site', name='Hébergement test', commune='Carcassonne', straight_line_distance_km=None))
        db.commit()
        def override():
            yield db
        app.dependency_overrides[get_db] = override
        with TestClient(app) as http:
            yield http, db
        app.dependency_overrides.clear()
    engine.dispose()

PROJECT = dict(departure_station_text='Toulouse', departure_date='2026-11-15', return_date='2026-11-15', student_count=20, supervisor_count=2, themes=['patrimoine'], destination_text='Carcassonne', selected_destination_id='cite-carcassonne', demo=True)

def create(http):
    response = http.post('/api/v1/sessions')
    assert response.status_code == 201
    return response.json()['session_id']

def test_structured_session_summary_reservation_and_feedback(client):
    http, db = client
    session_id = create(http)
    assert http.patch(f'/api/v1/sessions/{session_id}', json=PROJECT).status_code == 200
    summary = http.post('/api/trips/summary', json={'session_id': session_id, 'destination_id': 'cite-carcassonne'}).json()
    assert summary['project']['total_participants'] == 22
    assert summary['selected_train'] is None
    assert summary['chosen_destination']['name'] == 'Cité de Carcassonne'
    response = http.post('/api/prereservations', json={'session_id': session_id, 'contact_name': 'Test Enseignant', 'school_name': 'Collège Test', 'email': 'test@example.fr'})
    assert response.status_code == 200
    assert response.json()['status'] == 'pending'
    request = db.scalar(select(ReservationRequest))
    assert request.selected_itinerary['destination_id'] == 'cite-carcassonne'
    assert request.selected_itinerary['project']['student_count'] == 20
    assert 'Aucun envoi' in response.json()['message']
    assert http.post(f'/api/v1/sessions/{session_id}/feedback', json={'overall_rating': 4}).status_code == 200
    assert db.scalar(select(Feedback)).session_id == session_id

def test_historical_trains_require_opt_in(client):
    http, _ = client
    payload = dict(departure_station='Toulouse', destination_station='Carcassonne', departure_date='2026-11-15', total_participants=22)
    assert http.post('/api/trains/search', json=payload).status_code == 503
    data = http.post('/api/trains/search', json={**payload, 'demo': True}).json()
    assert data['data_status'] == 'historical_demo'
    assert data['results']
    assert data['results'][0]['group_capacity']['data_status'] == 'simulated'
    assert data['results'][0]['accessibility_site']['walking_minutes'] is None

def test_unknown_distance_and_duration_are_not_invented(client):
    http, _ = client
    result = http.post('/api/destinations/search', json={'max_train_minutes': 60, 'themes': ['patrimoine']}).json()
    assert result['duration_filter_applied'] is False
    assert result['warnings']
    assert any(item['distance_vol_oiseau_km'] is None for item in result['destinations'])
    assert next(item for item in result['destinations'] if item['id'] == 'cite-carcassonne')['distance_vol_oiseau_km'] > 0
    assert result['destinations'][0]['estimated_walking_minutes'] is None

@pytest.mark.parametrize('change', [{'student_count': 50, 'supervisor_count': 1}, {'return_date': '2026-11-14'}, {'departure_date': '2026-02-30'}])
def test_invalid_projects_rejected(client, change):
    http, _ = client
    session_id = create(http)
    assert http.patch(f'/api/v1/sessions/{session_id}', json={**PROJECT, **change}).status_code == 422

def test_clarification_accumulates_and_does_not_invent_origin(client):
    http, _ = client
    assert analyze_request('Je veux visiter Carcassonne avec 25 élèves le 2026-11-15')['departure_station_text'] is None
    data = http.post('/api/trips/analyze', json={'content': 'Sortie patrimoine pour 25 élèves.'}).json()
    result = http.post('/api/trips/analyze', json={'session_id': data['session_id'], 'content': 'Au départ de Toulouse le 2026-11-15.'}).json()
    assert result['extracted_data']['student_count'] == 25
    assert result['extracted_data']['departure_station_text'] == 'Toulouse'
    assert result['extracted_data']['missing_fields'] == []

def test_invalid_selected_train_rejected(client):
    http, _ = client
    session_id = create(http)
    http.patch(f'/api/v1/sessions/{session_id}', json=PROJECT)
    assert http.patch(f'/api/v1/sessions/{session_id}', json={**PROJECT, 'selected_train_number': 'fake'}).status_code == 422
    assert http.post('/api/trips/summary', json={'session_id': session_id, 'train_number': 'fake'}).status_code == 422

def test_invalid_and_spoken_dates_and_count_corrections():
    assert analyze_request('Au départ de Toulouse le 2026-02-30 pour 25 élèves sur le patrimoine')['departure_date'] is None
    result = analyze_request('Au départ de Toulouse le 15 novembre 2026 pour 25 élèves. Correction : 30 élèves et 4 accompagnateurs, patrimoine.')
    assert result['departure_date'] == '2026-11-15'
    assert result['student_count'] == 30
    assert result['total_participants'] == 34

def test_train_pair_persists_and_route_change_invalidates(client):
    from app.train_engine import find_train_options
    http, db = client
    session_id = create(http)
    http.patch(f'/api/v1/sessions/{session_id}', json=PROJECT)
    outbound = next(t for t in find_train_options('Toulouse', 'Carcassonne', 22) if t['group_capacity']['status'] == 'sufficient')
    inbound = next(t for t in find_train_options('Carcassonne', 'Toulouse', 22) if t['group_capacity']['status'] == 'sufficient' and t['departure_time'] > outbound['arrival_time'])
    chosen = {**PROJECT, 'selected_train_number': outbound['train_number'], 'selected_return_train_number': inbound['train_number']}
    assert http.patch(f'/api/v1/sessions/{session_id}', json=chosen).status_code == 200
    response = http.post('/api/trips/summary', json={'session_id': session_id})
    assert response.json()['selected_return_train'] == inbound['train_number']
    http.post('/api/prereservations', json={'session_id': session_id, 'contact_name': 'Test Enseignant', 'school_name': 'Collège Test', 'email': 'test@example.fr'})
    saved = db.scalar(select(ReservationRequest))
    assert saved.selected_itinerary['project']['selected_return_train_number'] == inbound['train_number']
    updated = http.patch(f'/api/v1/sessions/{session_id}', json={**chosen, 'departure_date': '2026-11-16', 'return_date': '2026-11-16'}).json()
    assert updated['project']['selected_train_number'] is None
    assert updated['project']['selected_return_train_number'] is None

def test_unknown_destination_in_specification_example():
    result = analyze_request('Je souhaite une sortie scolaire au départ de Toulouse le 2026-11-15 pour 30 élèves et 3 accompagnateurs. Je ne connais pas encore la destination et le thème est le patrimoine.')
    assert result['destination_text'] is None
    assert result['destination_known'] is False
    assert result['intent'] == 'discover_destination'
    assert result['missing_fields'] == []
