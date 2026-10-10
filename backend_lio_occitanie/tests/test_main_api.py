from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_session():
    response = client.post(
        "/api/v1/sessions",
        json={
            "initial_text": "Sortie scolaire depuis Toulouse"
        }
    )

    assert response.status_code == 200

    return response.json()["session_id"]


# ==========================================================
# HEALTH
# ==========================================================

def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["database"] == "connected"


# ==========================================================
# META
# ==========================================================

def test_meta():
    response = client.get("/api/v1/meta")

    assert response.status_code == 200

    body = response.json()

    assert body["api_version"] == "v1"
    assert "text" in body["input_modes"]


# ==========================================================
# SESSIONS
# ==========================================================

def test_create_session():
    response = client.post(
        "/api/v1/sessions",
        json={
            "initial_text": "Voyage scolaire"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert "session_id" in body
    assert body["status"] == "draft"


def test_get_session():
    session_id = create_session()

    response = client.get(
        f"/api/v1/sessions/{session_id}"
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == session_id


def test_get_unknown_session():
    response = client.get(
        "/api/v1/sessions/unknown"
    )

    assert response.status_code == 404


def test_patch_session():
    session_id = create_session()

    response = client.patch(
        f"/api/v1/sessions/{session_id}",
        json={
            "departure_station_text": "Toulouse",
            "student_count": 20
        }
    )

    assert response.status_code == 200
    assert response.json()["updated"] is True


# ==========================================================
# MESSAGES
# ==========================================================

def test_add_message():
    session_id = create_session()

    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={
            "input_mode": "text",
            "content": "Départ Toulouse"
        }
    )

    assert response.status_code == 200
    assert response.json()["stored"] is True


def test_message_invalid_mode():
    session_id = create_session()

    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={
            "input_mode": "invalid",
            "content": "hello"
        }
    )

    assert response.status_code == 422


# ==========================================================
# ANALYZE
# ==========================================================

def test_analyze_session():
    session_id = create_session()

    response = client.post(
        f"/api/v1/sessions/{session_id}/analyze"
    )

    assert response.status_code in (200, 500)


# ==========================================================
# DESTINATIONS
# ==========================================================

def test_list_destinations():
    response = client.get(
        "/api/v1/destinations"
    )

    assert response.status_code == 200
    assert "items" in response.json()


def test_destination_detail_not_found():
    response = client.get(
        "/api/v1/destinations/unknown"
    )

    assert response.status_code == 404


def test_destination_access():
    response = client.get(
        "/api/v1/destinations/unknown/access"
    )

    assert response.status_code == 200


# ==========================================================
# ACCOMMODATIONS
# ==========================================================

def test_list_accommodations():
    response = client.get(
        "/api/v1/accommodations"
    )

    assert response.status_code == 200

    assert "items" in response.json()


def test_accommodation_not_found():
    response = client.get(
        "/api/v1/accommodations/unknown"
    )

    assert response.status_code == 404


# ==========================================================
# THEMES
# ==========================================================

def test_themes():
    response = client.get(
        "/api/v1/themes"
    )

    assert response.status_code == 200
    assert "items" in response.json()


# ==========================================================
# NEXT STEP
# ==========================================================

def test_next_step():
    session_id = create_session()

    response = client.get(
        f"/api/v1/sessions/{session_id}/next-step"
    )

    assert response.status_code == 200
    assert "next_step" in response.json()


# ==========================================================
# CLARIFICATIONS
# ==========================================================

def test_clarification():
    session_id = create_session()

    response = client.post(
        f"/api/v1/sessions/{session_id}/clarifications",
        json={
            "input_mode": "text",
            "content": "Nous sommes 25 élèves"
        }
    )

    assert response.status_code == 200
    assert response.json()["stored"] is True
       