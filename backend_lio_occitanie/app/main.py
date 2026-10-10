import uuid
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from .db import Base, engine, get_db
from .models import Accommodation, ProjectSession, ReservationRequest, Feedback
from .llm import analyze_request
from .train_engine import find_train_options

# Initialisation des tables SQLite / PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Copilote Train liO Occitanie — Sorties Scolaires",
    version="1.0.0",
    description="API simplifiée pour le hackathon SNCF : de l'idée pédagogique à la pré-réservation vérifiée."
)

# ---------------------------------------------------------
# Schémas d'entrée / sortie Pydantic
# ---------------------------------------------------------
class TripAnalyzeIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=12000, description="Message en langage naturel ou transcription vocale")
    input_mode: str = Field("text", description="text ou speech_to_text")
    session_id: Optional[str] = Field(None, description="ID session existante pour enrichissement")

class DestinationSearchIn(BaseModel):
    session_id: Optional[str] = None
    themes: List[str] = []
    commune: Optional[str] = None
    department: Optional[str] = None
    max_train_minutes: Optional[int] = None

class TrainSearchIn(BaseModel):
    session_id: Optional[str] = None
    departure_station: str = Field(..., description="Gare ou ville de départ renseignée par l'enseignant")
    destination_station: str = Field(..., description="Gare d'arrivée liO")
    departure_date: Optional[str] = Field(None, description="Date de départ (ex: 2026-11-15)")
    total_participants: int = Field(30, ge=1, le=100, description="Élèves + accompagnateurs")
    walking_minutes: int = Field(15, ge=0, description="Temps estimé gare -> site")

class TripSummaryIn(BaseModel):
    session_id: str
    destination_id: Optional[str] = None
    train_number: Optional[str] = None

class PreReservationIn(BaseModel):
    session_id: str
    contact_name: str = Field(..., min_length=2)
    school_name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    phone: Optional[str] = None

class FeedbackIn(BaseModel):
    session_id: Optional[str] = None
    overall_rating: int = Field(..., ge=1, le=5, description="Note globale de 1 à 5")
    punctuality_rating: Optional[int] = Field(None, ge=1, le=5)
    pedagogical_rating: Optional[int] = Field(None, ge=1, le=5)
    accessibility_rating: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None


# ---------------------------------------------------------
# 1. Analyse du message et structuration du projet (LLM / Règles)
# ---------------------------------------------------------
@app.post("/api/trips/analyze", summary="Analyse du besoin en langage naturel")
@app.post("/api/v1/sessions/analyze")
def analyze_trip(body: TripAnalyzeIn, db: Session = Depends(get_db)):
    """
    Point d'entrée unique de la saisie enseignant (écrite ou vocale transcrite).
    Extrait la gare de départ, les effectifs, la date, le thème et vérifie la faisabilité.
    """
    analysis = analyze_request(body.content)

    # Création ou reprise de la session
    if body.session_id:
        session_obj = db.get(ProjectSession, body.session_id)
        if not session_obj:
            raise HTTPException(404, detail="Session non trouvée")
        session_obj.original_request = body.content
        session_obj.input_mode = body.input_mode
    else:
        session_obj = ProjectSession(
            original_request=body.content,
            input_mode=body.input_mode
        )
        db.add(session_obj)

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


# ---------------------------------------------------------
# 2. Recherche et suggestions de destinations
# ---------------------------------------------------------
@app.post("/api/destinations/search", summary="Recherche de destinations adaptées au projet")
def search_destinations(body: DestinationSearchIn, db: Session = Depends(get_db)):
    """
    Propose des hébergements et sites touristiques d'Occitanie reliés au réseau liO.
    Calcule le temps piéton gare -> site et vérifie l'accessibilité scolaire.
    """
    stmt = select(Accommodation)
    if body.themes:
        stmt = stmt.where(or_(*[Accommodation.themes_raw.ilike(f"%{t}%") for t in body.themes]))
    if body.commune:
        stmt = stmt.where(Accommodation.commune.ilike(f"%{body.commune}%"))
    if body.department:
        stmt = stmt.where(Accommodation.department.ilike(f"%{body.department}%"))

    rows = db.scalars(stmt.limit(30)).all()

    items = []
    for acc in rows:
        dist_km = acc.straight_line_distance_km or 0.0
        # Estimation marche groupe scolaire : 15 min par km (4 km/h)
        walk_min = int(round(dist_km * 15))
        is_ok_walking = walk_min <= 20

        items.append({
            "id": acc.id,
            "name": acc.name,
            "commune": acc.commune,
            "department": acc.department,
            "themes": acc.themes_raw,
            "nearest_station": acc.nearest_station_raw,
            "distance_vol_oiseau_km": dist_km,
            "estimated_walking_minutes": walk_min,
            "accessibility_verdict": (
                "🟢 Accès direct à pied (≤ 20 min)"
                if is_ok_walking
                else "🟡 Transport urbain / navette conseillée (> 20 min)"
            ),
            "capacity": acc.total_capacity,
            "nearby_activities": acc.nearby_sites_raw,
            "website": acc.website_url,
            "nature_label": acc.nature_label
        })

    return {
        "count": len(items),
        "destinations": items,
        "advice": "Sélectionnez un site pour afficher les trains liO correspondants."
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

    trains = find_train_options(
        origin=dep_station,
        destination_station=dest_station,
        requested_pax=pax,
        walking_minutes=walk_min
    )

    return {
        "departure_station": dep_station,
        "arrival_station": dest_station,
        "departure_date": dep_date or "2026-11-15",
        "requested_travelers": pax,
        "trains_count": len(trains),
        "results": trains,
        "policy_notice": "Seuls les trains liO ouverts aux groupes (max 50 pax) sont affichés."
    }


# ---------------------------------------------------------
# 4. Récapitulatif du voyage
# ---------------------------------------------------------
@app.post("/api/trips/summary", summary="Synthèse complète du projet avant réservation")
def trip_summary(body: TripSummaryIn, db: Session = Depends(get_db)):
    session_obj = db.get(ProjectSession, body.session_id)
    if not session_obj:
        raise HTTPException(404, detail="Session non trouvée")

    acc = db.get(Accommodation, body.destination_id) if body.destination_id else None

    return {
        "session_id": session_obj.id,
        "status": session_obj.status,
        "project": {
            "departure_station": session_obj.departure_station_text,
            "departure_date": session_obj.departure_date,
            "class_level": session_obj.class_level,
            "students": session_obj.student_count,
            "supervisors": session_obj.supervisor_count,
            "total_participants": (session_obj.student_count or 0) + (session_obj.supervisor_count or 0)
        },
        "chosen_destination": {
            "name": acc.name if acc else session_obj.destination_text,
            "commune": acc.commune if acc else None,
            "department": acc.department if acc else None,
            "nearest_station": acc.nearest_station_raw if acc else None
        },
        "selected_train": body.train_number or "Train liO direct du matin",
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

    ref_code = f"LIO-2026-{uuid.uuid4().hex[:6].upper()}"
    req = ReservationRequest(
        reference_code=ref_code,
        session_id=body.session_id,
        contact_name=body.contact_name,
        school_name=body.school_name,
        email=body.email,
        phone=body.phone,
        status="pending"
    )
    db.add(req)
    session_obj.status = "reservation_pending"
    db.commit()
    db.refresh(req)

    return {
        "reference_code": req.reference_code,
        "status": "pending",
        "message": "Demande de pré-réservation transmise — confirmation en attente.",
        "contact": req.contact_name,
        "school": req.school_name,
        "submitted_at": req.submitted_at.isoformat()
    }


# ---------------------------------------------------------
# 6. Retour d'expérience après sortie
# ---------------------------------------------------------
@app.post("/api/feedback", summary="Enregistrer un retour d'expérience après voyage")
@app.post("/api/v1/sessions/{session_id}/feedback")
def submit_feedback(body: FeedbackIn, db: Session = Depends(get_db)):
    fb = Feedback(
        session_id=body.session_id,
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
