import uuid
import os
import re
from datetime import date, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from .db import Base, engine, get_db
from .models import Accommodation, ProjectSession, ReservationRequest, Feedback
from .llm import LLMClient
from .train_engine import find_train_options
from .stt import transcribe_audio_bytes
from .attractions import attraction_by_id, search_attractions, stations, canonical_theme
from .llm.school import analyze_school_request
from .visit_pedagogy import evaluate_visit
from .web_pedagogy import assess_visit
from .walking import walking_route, closest_station

# Initialisation du client LLM et de l'extracteur de voyage
llm_client = LLMClient()

TEST_FRONTEND = Path(__file__).resolve().parent.parent / "test_frontend" / "index.html"

# Initialisation des tables SQLite / PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Copilote Train liO Occitanie — Sorties Scolaires",
    version="1.0.0",
    description="API unifiée pour le hackathon SNCF : intégration Speech-to-Text Whisper, recherche liO et pré-réservation."
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


@app.get("/test", include_in_schema=False)
def test_frontend():
    """Page HTML de test manuel de toutes les routes de l'API (dont l'enregistrement vocal)."""
    if not TEST_FRONTEND.is_file():
        raise HTTPException(404, detail="test_frontend/index.html introuvable")
    return FileResponse(TEST_FRONTEND)

# ---------------------------------------------------------
# Schémas d'entrée / sortie Pydantic
# ---------------------------------------------------------
class TripAnalyzeIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=12000, description="Message en langage naturel ou transcription vocale")
    input_mode: str = Field("text", description="text ou speech_to_text")
    session_id: Optional[str] = Field(None, description="ID session existante pour enrichissement")

class DestinationSearchIn(BaseModel):
    session_id: Optional[str] = None
    themes: List[str] = Field(default_factory=list)
    commune: Optional[str] = None
    department: Optional[str] = None
    max_train_minutes: Optional[int] = None
    destination_station: Optional[str] = Field(None, min_length=2, max_length=250)
    search_mode: Optional[str] = Field(None, pattern="^(station|theme)$")
    radius_km: float = Field(5, ge=0.1, le=100)
    class_level: Optional[str] = Field(None, max_length=50)

class TrainSearchIn(BaseModel):
    session_id: Optional[str] = None
    departure_station: str = Field(..., description="Gare ou ville de départ renseignée par l'enseignant")
    destination_station: str = Field(..., description="Gare d'arrivée liO")
    departure_date: date
    return_date: Optional[date] = None
    total_participants: int = Field(30, ge=1, le=100, description="Élèves + accompagnateurs")
    walking_minutes: int = Field(15, ge=0, description="Temps estimé gare -> site")
    demo: bool = False

class TripSummaryIn(BaseModel):
    session_id: str
    destination_id: Optional[str] = None
    train_number: Optional[str] = None

class PreReservationIn(BaseModel):
    session_id: str
    contact_name: str = Field(..., min_length=2, max_length=200)
    school_name: str = Field(..., min_length=2, max_length=250)
    email: str = Field(..., min_length=5, max_length=250)
    phone: Optional[str] = Field(None, max_length=50)

class FeedbackIn(BaseModel):
    session_id: Optional[str] = None
    overall_rating: int = Field(..., ge=1, le=5, description="Note globale de 1 à 5")
    punctuality_rating: Optional[int] = Field(None, ge=1, le=5)
    pedagogical_rating: Optional[int] = Field(None, ge=1, le=5)
    accessibility_rating: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=4000)


class SessionUpdate(BaseModel):
    departure_station_text: str = Field(..., min_length=2, max_length=250)
    departure_date: date
    return_date: Optional[date] = None
    class_level: Optional[str] = Field(None, max_length=50)
    student_count: int = Field(..., ge=1, le=100)
    supervisor_count: int = Field(0, ge=0, le=99)
    themes: List[str] = Field(default_factory=list)
    duration_days: int = Field(1, ge=1, le=30)
    departure_place: Optional[str] = Field(None, max_length=300)
    destination_text: Optional[str] = Field(None, max_length=300)
    selected_destination_id: Optional[str] = None
    selected_train_number: Optional[str] = None
    selected_return_train_number: Optional[str] = None
    demo: bool = False


def session_payload(session_obj):
    return {
        "session_id": session_obj.id, "status": session_obj.status,
        "project": session_obj.structured_request or {},
        "selected_destination_id": (session_obj.structured_request or {}).get("selected_destination_id"),
        "selected_train_number": session_obj.selected_train_number,
    }


@app.post("/api/v1/sessions", status_code=201)
def create_session(db: Session = Depends(get_db)):
    session_obj = ProjectSession()
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_payload(session_obj)


@app.get("/api/v1/sessions/{session_id}")
def read_session(session_id: str, db: Session = Depends(get_db)):
    session_obj = db.get(ProjectSession, session_id)
    if not session_obj:
        raise HTTPException(404, detail="Session non trouvée")
    return session_payload(session_obj)


@app.patch("/api/v1/sessions/{session_id}")
def update_session(session_id: str, body: SessionUpdate, db: Session = Depends(get_db)):
    session_obj = db.get(ProjectSession, session_id)
    if not session_obj:
        raise HTTPException(404, detail="Session non trouvée")
    if body.return_date and body.return_date < body.departure_date:
        raise HTTPException(422, detail="La date de retour précède le départ.")
    if body.student_count + body.supervisor_count > 50:
        raise HTTPException(422, detail="Un groupe liO ne peut pas dépasser 50 voyageurs par train.")
    if len(body.themes) > 1:
        raise HTTPException(422, detail="Choisissez un seul thème pédagogique par projet.")
    if body.selected_destination_id and not attraction_by_id(body.selected_destination_id):
        raise HTTPException(404, detail="Attraction non trouvée")
    data = body.model_dump(mode="json")
    previous = session_obj.structured_request or {}
    # Les changements de trajet rendent les anciennes sélections caduques.
    route_keys = ("departure_station_text", "departure_date", "return_date", "destination_text", "student_count", "supervisor_count", "demo")
    changed = any(previous.get(key) != data.get(key) for key in route_keys)
    if changed:
        data["selected_train_number"] = None
        data["selected_return_train_number"] = None
    selected = {}
    for key, origin, destination in (
        ("selected_train_number", body.departure_station_text, body.destination_text),
        ("selected_return_train_number", body.destination_text, body.departure_station_text),
    ):
        if data.get(key):
            if not body.demo:
                raise HTTPException(422, detail="Un train historique nécessite le mode démonstration.")
            options = find_train_options(origin or "", destination or "", body.student_count + body.supervisor_count)
            match = next((t for t in options if t["train_number"] == data[key]), None)
            if not match or match["group_capacity"]["status"] != "sufficient":
                raise HTTPException(422, detail="Train sélectionné incompatible avec le trajet ou la jauge de démonstration.")
            selected[key] = match
    if len(selected) == 2 and (body.return_date or body.departure_date) == body.departure_date:
        if selected["selected_return_train_number"]["departure_time"] <= selected["selected_train_number"]["arrival_time"]:
            raise HTTPException(422, detail="Le retour doit partir après l'arrivée du train aller.")
    for key in ("departure_station_text", "departure_date", "class_level", "student_count", "supervisor_count", "destination_text", "selected_train_number"):
        setattr(session_obj, key, data[key])
    data["pedagogical_profile"] = previous.get("pedagogical_profile")
    if data["pedagogical_profile"] and any(previous.get(key) != data.get(key) for key in ("class_level", "themes")):
        data["pedagogical_profile"] = None
    session_obj.structured_request = data
    session_obj.status = "ready_for_destinations"
    db.commit()
    return session_payload(session_obj)


# ---------------------------------------------------------
# 1. Analyse textuelle ou vocale (Speech-to-Text Whisper)
# ---------------------------------------------------------
@app.post("/api/trips/analyze", summary="Analyse du besoin en texte libre")
@app.post("/api/v1/sessions/analyze")
def analyze_trip(body: TripAnalyzeIn, db: Session = Depends(get_db)):
    """
    Point d'entrée de la saisie écrite : extrait la gare de départ, les effectifs,
    la date, le thème et initialise ou met à jour la session.
    """
    if body.session_id:
        session_obj = db.get(ProjectSession, body.session_id)
        if not session_obj:
            raise HTTPException(404, detail="Session non trouvée")
        session_obj.original_request = "\n".join(filter(None, [session_obj.original_request, body.content]))[-12000:]
        session_obj.input_mode = body.input_mode
    else:
        session_obj = ProjectSession(
            original_request=body.content,
            input_mode=body.input_mode
        )
        db.add(session_obj)

    analysis = analyze_school_request(session_obj.original_request, llm_client)
    session_obj.structured_request = analysis
    session_obj.departure_station_text = analysis.get("departure_station_text")
    session_obj.departure_date = analysis.get("departure_date")
    session_obj.class_level = analysis.get("class_level")
    session_obj.student_count = analysis.get("student_count")
    session_obj.supervisor_count = analysis.get("supervisor_count")
    session_obj.destination_text = analysis.get("destination_text")
    session_obj.status = "needs_clarification" if analysis.get("missing_fields") else "ready_for_destinations"

    db.commit()
    db.refresh(session_obj)

    return {
        "session_id": session_obj.id,
        "status": session_obj.status,
        "input_mode": session_obj.input_mode,
        "extracted_data": analysis,
        "next_step": "destinations_search" if not analysis.get("missing_fields") else "clarification"
    }

def postprocess_voice(analysis):
    from .llm.schemas import TravelInfo
    return TravelInfo(nombre_personnes=analysis["total_participants"] or None,
                      date_depart=analysis["departure_date"], date_retour=analysis.get("return_date"),
                      lieu_depart=analysis["departure_station_text"], destination=analysis["destination_text"],
                      destination_connue=analysis["destination_known"])

@app.post("/api/analyzeVoice", summary="Analyse audio : WhisperAI local (audio -> texte) puis LLM local (texte -> catégories JSON)")
def analyze_voice(
    file: UploadFile = File(..., description="Fichier audio enregistré (WAV, WebM, MP3, OGG...)"),
    language: str = Form("fr", description="Code langue Whisper (fr, en...)"),
):
    """
    1. Reçoit le fichier audio en entrée.
    2. Le transmet au modèle local WhisperAI pour obtenir la retranscription en texte.
    3. Transmet la retranscription obtenue en entrée au LLM local (TravelExtractor).
    4. Retourne les catégories obtenues au format JSON (avec null si un élément n'est pas renseigné).
    """
    audio_bytes = file.file.read()
    if not audio_bytes:
        raise HTTPException(400, detail="Fichier audio vide.")

    try:
        transcription = transcribe_audio_bytes(audio_bytes, filename=file.filename or "audio.wav", language=language)
    except FileNotFoundError as exc:
        raise HTTPException(503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(500, detail=f"Erreur de transcription audio : {exc}")

    if not transcription:
        return {
            "transcription": "",
            "nombre_personnes": None,
            "date_depart": None,
            "date_retour": None,
            "lieu_depart": None,
            "destination": None,
            "destination_connue": False,
            "speech_detected": False,
        }

    # Appel au modèle LLM local pour classifier et extraire les catégories en JSON
    analysis = analyze_school_request(transcription, llm_client)
    travel_info = postprocess_voice(analysis)

    return {
        "transcription": transcription,
        "nombre_personnes": travel_info.nombre_personnes,
        "date_depart": travel_info.date_depart,
        "date_retour": travel_info.date_retour,
        "lieu_depart": travel_info.lieu_depart,
        "destination": travel_info.destination,
        "destination_connue": travel_info.destination_connue,
        "speech_detected": True,
        "extracted_data": analysis,
        "pedagogical_profile": analysis["pedagogical_profile"],
        "analysis_mode": analysis["analysis_mode"],
    }


# ---------------------------------------------------------
# 2. Recherche et suggestions de destinations
# ---------------------------------------------------------
@app.get("/api/stations", summary="Gares voyageurs géolocalisées d’Occitanie")
def list_stations():
    return {"stations": stations(), "source_url": "https://data.sncf.com/explore/dataset/liste-des-gares/", "license": "ODbL"}

@app.get("/api/destinations/{destination_id}/walking", summary="Marche depuis la gare la plus proche")
def destination_walking(destination_id: str):
    item = attraction_by_id(destination_id)
    if not item:
        raise HTTPException(404, detail="Attraction non trouvée")
    return walking_route(item)

def assessment_context(body: DestinationSearchIn, db: Session):
    session_obj = db.get(ProjectSession, body.session_id) if body.session_id else None
    if body.session_id and not session_obj:
        raise HTTPException(404, detail="Session non trouvée")
    project = (session_obj.structured_request or {}) if session_obj else {}
    themes = body.themes or project.get("themes", [])
    context = {**project, "themes": themes, "class_level": body.class_level or project.get("class_level")}
    if ((body.themes and body.themes != project.get("themes", []))
            or (body.class_level and body.class_level != project.get("class_level"))):
        context["pedagogical_profile"] = None
    return context


@app.post("/api/destinations/{destination_id}/assessment", summary="Analyse pédagogique sourcée par le LLM local")
def destination_assessment(destination_id: str, body: DestinationSearchIn, db: Session = Depends(get_db)):
    item = attraction_by_id(destination_id)
    if not item:
        raise HTTPException(404, detail="Attraction non trouvée")
    return assess_visit(item, assessment_context(body, db), llm_client)

@app.post("/api/destinations/search", summary="Recherche de destinations adaptées au projet")
def search_destinations(body: DestinationSearchIn, db: Session = Depends(get_db)):
    session_obj = db.get(ProjectSession, body.session_id) if body.session_id else None
    if body.session_id and not session_obj:
        raise HTTPException(404, detail="Session non trouvée")
    project = (session_obj.structured_request or {}) if session_obj else {}
    station = None if body.search_mode == "theme" else body.destination_station or (session_obj.destination_text if session_obj else None)
    if body.search_mode == "station" and not station:
        raise HTTPException(422, detail="Renseignez la gare de destination.")
    themes = body.themes or project.get("themes", [])
    if not station and len(themes) != 1:
        raise HTTPException(422, detail="Destination inconnue : choisissez un seul thème pédagogique.")
    if not station and not canonical_theme(themes[0]):
        raise HTTPException(422, detail="Thème pédagogique non reconnu.")
    try:
        items = search_attractions(station=station, theme=themes[0] if themes else None,
                                  commune=body.commune, department=body.department, radius_km=body.radius_km)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    context = assessment_context(body, db)
    for item in items:
        item["pedagogical_assessment"] = evaluate_visit(item, context)
        item["assessment_context"] = body.model_dump()
        nearest = closest_station(item)
        item["closest_station"] = nearest["name"] if nearest else None
    return {
        "count": len(items), "destinations": items,
        "search_mode": "station" if station else "theme",
        "radius_km": body.radius_km if station else None,
        "advice": "Distance à vol d’oiseau depuis les coordonnées officielles des sites et des gares. Accès et accueil scolaire à confirmer.",
        "duration_filter_applied": False,
        "warnings": ["Le filtre de durée n'est pas vérifiable sans horaires actualisés."] if body.max_train_minutes else [],
    }


# ---------------------------------------------------------
# 3. Recherche des trains liO + Jauge 50 pax + Indice Confiance
# ---------------------------------------------------------
@app.post("/api/trains/search", summary="Recherche de trains liO avec Jauge et Confiance")
@app.post("/api/v1/sessions/{session_id}/train-search")
def search_trains(
    body: Optional[TrainSearchIn] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Recherche les horaires réels liO (février-juin 2026), calcule la jauge de 50 places
    et l'Indicateur 'Confiance Voyageur Scolaire' (/100) basé sur la régularité et les suppressions.
    """
    dep_station = ""
    dest_station = ""
    pax = 30
    walk_min = 15
    dep_date = None

    if body:
        dep_station = body.departure_station
        dest_station = body.destination_station
        pax = body.total_participants
        walk_min = body.walking_minutes
        dep_date = body.departure_date
    elif session_id:
        sess = db.get(ProjectSession, session_id)
        if not sess:
            raise HTTPException(404, detail="Session non trouvée")
        dep_station = sess.departure_station_text or ""
        dest_station = sess.destination_text or ""
        pax = (sess.student_count or 0) + (sess.supervisor_count or 0) or 30
        dep_date = sess.departure_date

    if not dep_station or not dest_station:
        raise HTTPException(400, detail="Gare de départ et gare d'arrivée requises.")

    if not body or not body.demo:
        raise HTTPException(503, detail="Aucune source d'horaires actualisés et de disponibilités groupes n'est connectée. Vous pouvez consulter les données historiques en mode démonstration.")
    if body.return_date and body.return_date < body.departure_date:
        raise HTTPException(422, detail="La date de retour précède le départ.")
    if pax > 50:
        raise HTTPException(422, detail="Un groupe liO ne peut pas dépasser 50 voyageurs par train.")

    trains = find_train_options(
        origin=dep_station,
        destination_station=dest_station,
        requested_pax=pax,
        walking_minutes=walk_min
    )

    for train in trains:
        train["data_status"] = "historical_demo"
        train["group_capacity"]["data_status"] = "simulated"
        train["group_capacity"]["message"] = "Jauge simulée pour la démonstration ; disponibilité réelle inconnue."
        train["accessibility_site"] = {"walking_minutes": None, "is_under_20_min": None, "label": "Accès gare → site non vérifié"}
        train["confidence_indicator"]["data_status"] = "simulated"
        train["confidence_indicator"]["explanation"] = "Score de démonstration : historique ferroviaire, valeurs de repli, jauge et accès simulés. Il ne permet pas de confirmer la faisabilité."

    return {
        "departure_station": dep_station,
        "arrival_station": dest_station,
        "departure_date": dep_date,
        "requested_travelers": pax,
        "trains_count": len(trains),
        "results": trains,
        "data_status": "historical_demo",
        "source_name": "Détail desserte (1).xlsx / Data_Hackathon.csv",
        "policy_notice": "Démonstration historique (février–juin 2026), journée type. Horaires non validés pour votre date ; autorisation groupes à vérifier. Jauge simulée, aucune disponibilité réelle.",
    }


# ---------------------------------------------------------
# 4. Récapitulatif du voyage
# ---------------------------------------------------------
@app.post("/api/trips/summary", summary="Synthèse complète du projet avant réservation")
def trip_summary(body: TripSummaryIn, db: Session = Depends(get_db)):
    session_obj = db.get(ProjectSession, body.session_id)
    if not session_obj:
        raise HTTPException(404, detail="Session non trouvée")

    destination_id = body.destination_id or (session_obj.structured_request or {}).get("selected_destination_id")
    acc = attraction_by_id(destination_id) if destination_id else None
    if destination_id and not acc:
        raise HTTPException(404, detail="Attraction non trouvée")
    saved_destination = (session_obj.structured_request or {}).get("selected_destination_id")
    if body.destination_id and saved_destination and body.destination_id != saved_destination:
        raise HTTPException(422, detail="L'attraction doit être sélectionnée dans le projet avant le récapitulatif.")
    if body.destination_id:
        session_obj.structured_request = {**(session_obj.structured_request or {}), "selected_destination_id": body.destination_id}
    if body.train_number and body.train_number != session_obj.selected_train_number:
        raise HTTPException(422, detail="Le train doit être sélectionné et validé dans la session.")
    db.commit()
    project = session_obj.structured_request or {}

    return {
        "session_id": session_obj.id,
        "status": session_obj.status,
        "project": {
            "departure_station": session_obj.departure_station_text,
            "departure_date": session_obj.departure_date,
            "class_level": session_obj.class_level,
            "students": session_obj.student_count,
            "supervisors": session_obj.supervisor_count,
            "total_participants": (session_obj.student_count or 0) + (session_obj.supervisor_count or 0),
            "return_date": project.get("return_date"),
            "duration_days": project.get("duration_days", 1),
            "departure_place": project.get("departure_place"),
            "themes": project.get("themes", []),
            "pedagogical_profile": project.get("pedagogical_profile"),
        },
        "chosen_destination": {
            "name": acc["name"] if acc else session_obj.destination_text,
            "commune": acc["commune"] if acc else None,
            "department": acc["department"] if acc else None,
            "nearest_station": acc["nearest_station"] if acc else None
        },
        "selected_train": session_obj.selected_train_number,
        "selected_return_train": project.get("selected_return_train_number"),
        "demo": project.get("demo", False),
        "official_disclaimer": "Une demande de pré-réservation n'est pas un billet confirmé ; une validation liO est requise."
    }


# ---------------------------------------------------------
# 5. Demande de pré-réservation
# ---------------------------------------------------------
@app.post("/api/prereservations", summary="Créer une demande de pré-réservation")
@app.post("/api/v1/reservation-requests")
def create_prereservation(body: PreReservationIn, db: Session = Depends(get_db)):
    session_obj = db.get(ProjectSession, body.session_id)
    if not session_obj:
        raise HTTPException(404, detail="Session non trouvée")
    if not all((session_obj.departure_station_text, session_obj.departure_date, session_obj.student_count, session_obj.destination_text)):
        raise HTTPException(422, detail="Confirmez le départ, la date, les effectifs et la destination avant de créer une demande.")

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", body.email):
        raise HTTPException(422, detail="Adresse email invalide.")
    ref_code = f"LIO-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"
    req = ReservationRequest(
        reference_code=ref_code,
        session_id=body.session_id,
        contact_name=body.contact_name,
        school_name=body.school_name,
        email=body.email,
        phone=body.phone,
        status="pending",
        selected_itinerary={
            "project": session_obj.structured_request,
            "destination_id": (session_obj.structured_request or {}).get("selected_destination_id"),
            "train_number": session_obj.selected_train_number,
            "data_status": "historical_demo" if (session_obj.structured_request or {}).get("demo") else "unverified",
        },
    )
    db.add(req)
    session_obj.status = "reservation_pending"
    db.commit()
    db.refresh(req)

    return {
        "reference_code": req.reference_code,
        "status": "pending",
        "message": "Demande enregistrée dans le prototype — validation en attente. Aucun envoi à SNCF liO ni email automatique.",
        "contact": req.contact_name,
        "school": req.school_name,
        "submitted_at": req.submitted_at.replace(tzinfo=timezone.utc).isoformat()
    }


# ---------------------------------------------------------
# 6. Retour d'expérience après sortie
# ---------------------------------------------------------
@app.post("/api/feedback", summary="Enregistrer un retour d'expérience après voyage")
@app.post("/api/v1/sessions/{session_id}/feedback")
def submit_feedback(body: FeedbackIn, session_id: Optional[str] = None, db: Session = Depends(get_db)):
    resolved_id = session_id or body.session_id
    if resolved_id and not db.get(ProjectSession, resolved_id):
        raise HTTPException(404, detail="Session non trouvée")
    fb = Feedback(
        session_id=resolved_id,
        overall_rating=body.overall_rating,
        punctuality_rating=body.punctuality_rating,
        pedagogical_rating=body.pedagogical_rating,
        accessibility_rating=body.accessibility_rating,
        comments=body.comments
    )
    db.add(fb)
    db.commit()

    return {
        "status": "recorded",
        "message": "Merci ! Votre retour d'expérience permet d'affiner l'Indicateur Confiance Voyageur Scolaire."
    }


# ---------------------------------------------------------
# Utilitaires & Compatibilité
# ---------------------------------------------------------
@app.get("/health", summary="Vérification santé de l'API")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "service": "lio-copilote-backend", "database": "connected"}

@app.get("/api/v1/accommodations", summary="Liste des hébergements scolaires")
def list_accommodations(
    q: Optional[str] = None,
    theme: Optional[str] = None,
    commune: Optional[str] = None,
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    stmt = select(Accommodation)
    if q:
        stmt = stmt.where(or_(Accommodation.name.ilike(f"%{q}%"), Accommodation.nearby_sites_raw.ilike(f"%{q}%")))
    if theme:
        stmt = stmt.where(Accommodation.themes_raw.ilike(f"%{theme}%"))
    if commune:
        stmt = stmt.where(Accommodation.commune.ilike(f"%{commune}%"))
    if department:
        stmt = stmt.where(Accommodation.department.ilike(f"%{department}%"))

    rows = db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()
    return {
        "items": [
            {
                "id": a.id, "name": a.name, "commune": a.commune, "department": a.department,
                "themes": a.themes_raw, "capacity": a.total_capacity,
                "nearest_station": a.nearest_station_raw, "distance_vol_oiseau_km": a.straight_line_distance_km
            } for a in rows
        ],
        "page": page,
        "limit": limit
    }
