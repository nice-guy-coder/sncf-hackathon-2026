from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from .db import Base, engine, get_db
from .models import Accommodation, ProjectSession, ConversationMessage, Destination, ReservationRequest, Feedback
from .llm import analyze_request
Base.metadata.create_all(bind=engine)
app=FastAPI(title="Backend liO — sorties scolaires Occitanie",version="0.1.0",
 description="Prototype. La recherche ferroviaire attend une source actualisée.")
class SessionIn(BaseModel): initial_text:str|None=None
class MessageIn(BaseModel):
    input_mode:str="text"
    content:str=Field(min_length=1,max_length=12000)
class DestinationSearchIn(BaseModel):
    themes:list[str]=[]
    max_train_minutes:int|None=None
    commune:str|None=None
    department:str|None=None
class SelectIn(BaseModel): destination_text:str=Field(min_length=1,max_length=300)
class ReservationIn(BaseModel):
    session_id:str
    contact_name:str
    school_name:str
    email:str

@app.get("/health")
def health(db:Session=Depends(get_db)):
    db.execute(select(1)); return {"status":"ok","database":"connected"}
@app.get("/api/v1/meta")
def meta():
    return {"api_version":"v1","region":"Occitanie","input_modes":["text","speech_to_text"],
            "classical_form":False,"train_source_configured":False}
@app.get("/api/v1/destinations")
def destinations(q:str|None=None,commune:str|None=None,department:str|None=None,
                 page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    stmt=select(Destination)
    if q: stmt=stmt.where(Destination.name.ilike(f"%{q}%"))
    if commune: stmt=stmt.where(Destination.commune.ilike(f"%{commune}%"))
    if department: stmt=stmt.where(Destination.department.ilike(f"%{department}%"))
    rows=db.scalars(stmt.offset((page-1)*limit).limit(limit)).all()
    return {"items":[{"id":d.id,"name":d.name,"commune":d.commune,"department":d.department} for d in rows],"page":page,"limit":limit}
@app.get("/api/v1/accommodations")
def accommodations(q:str|None=None,theme:str|None=None,commune:str|None=None,department:str|None=None,
                   min_capacity:int|None=None,page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    stmt=select(Accommodation)
    if q: stmt=stmt.where(or_(Accommodation.name.ilike(f"%{q}%"),Accommodation.nearby_sites_raw.ilike(f"%{q}%")))
    if theme: stmt=stmt.where(Accommodation.themes_raw.ilike(f"%{theme}%"))
    if commune: stmt=stmt.where(Accommodation.commune.ilike(f"%{commune}%"))
    if department: stmt=stmt.where(Accommodation.department.ilike(f"%{department}%"))
    if min_capacity is not None: stmt=stmt.where(Accommodation.total_capacity>=min_capacity)
    rows=db.scalars(stmt.order_by(Accommodation.name).offset((page-1)*limit).limit(limit)).all()
    return {"items":[{"id":a.id,"name":a.name,"commune":a.commune,"department":a.department,
      "themes":a.themes_raw,"capacity":a.total_capacity,"student_beds":a.student_beds,
      "supervisor_beds":a.supervisor_beds,"nearest_station":a.nearest_station_raw,
      "distance_vol_oiseau_km":a.straight_line_distance_km,"website":a.website_url,"permalink":a.permalink}
      for a in rows],"page":page,"limit":limit}
@app.post("/api/v1/sessions")
def create_session(body:SessionIn,db:Session=Depends(get_db)):
    s=ProjectSession(original_request=body.initial_text,status="draft"); db.add(s); db.commit(); db.refresh(s)
    if body.initial_text:
        db.add(ConversationMessage(session_id=s.id,content=body.initial_text,input_mode="text")); db.commit()
    return {"session_id":s.id,"status":s.status}
@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id:str,db:Session=Depends(get_db)):
    s=db.get(ProjectSession,session_id)
    if not s: raise HTTPException(404,detail={"code":"session_not_found"})
    return {"session_id":s.id,"status":s.status,"request":s.original_request,"structured_request":s.structured_request,
      "departure_station":s.departure_station_text,"departure_date":s.departure_date,
      "student_count":s.student_count,"supervisor_count":s.supervisor_count,"destination":s.destination_text}
@app.post("/api/v1/sessions/{session_id}/messages")
def add_message(session_id:str,body:MessageIn,db:Session=Depends(get_db)):
    s=db.get(ProjectSession,session_id)
    if not s: raise HTTPException(404,detail={"code":"session_not_found"})
    if body.input_mode not in ("text","speech_to_text"): raise HTTPException(422,detail="input_mode doit être text ou speech_to_text")
    db.add(ConversationMessage(session_id=session_id,content=body.content,input_mode=body.input_mode))
    s.original_request=body.content; db.commit()
    return {"stored":True,"session_id":session_id}
@app.post("/api/v1/sessions/{session_id}/analyze")
def analyze(session_id:str,db:Session=Depends(get_db)):
    s=db.get(ProjectSession,session_id)
    if not s: raise HTTPException(404,detail={"code":"session_not_found"})
    if not s.original_request: raise HTTPException(400,detail={"code":"empty_request"})
    data=analyze_request(s.original_request); s.structured_request=data
    s.departure_station_text=data.get("departure_station_text"); s.departure_date=data.get("departure_date")
    s.student_count=data.get("student_count"); s.supervisor_count=data.get("supervisor_count")
    s.destination_text=data.get("destination_text"); s.status="needs_clarification" if data["missing_fields"] else "analyzed"
    db.commit(); return data
@app.post("/api/v1/sessions/{session_id}/destination-search")
def destination_search(session_id:str,body:DestinationSearchIn,db:Session=Depends(get_db)):
    s=db.get(ProjectSession,session_id)
    if not s: raise HTTPException(404,detail={"code":"session_not_found"})
    stmt=select(Accommodation)
    if body.themes: stmt=stmt.where(or_(*[Accommodation.themes_raw.ilike(f"%{t}%") for t in body.themes]))
    if body.commune: stmt=stmt.where(Accommodation.commune.ilike(f"%{body.commune}%"))
    if body.department: stmt=stmt.where(Accommodation.department.ilike(f"%{body.department}%"))
    rows=db.scalars(stmt.limit(50)).all()
    return {"items":[{"accommodation_id":a.id,"name":a.name,"commune":a.commune,"department":a.department,
      "themes":a.themes_raw,"nearest_station":a.nearest_station_raw,"distance_vol_oiseau_km":a.straight_line_distance_km}
      for a in rows],"notice":"Suggestions fondées sur les données d’hébergement disponibles ; la durée de trajet n’est pas calculable sans données ferroviaires vérifiées."}
@app.post("/api/v1/sessions/{session_id}/destination-selection")
def select_destination(session_id:str,body:SelectIn,db:Session=Depends(get_db)):
    s=db.get(ProjectSession,session_id)
    if not s: raise HTTPException(404,detail={"code":"session_not_found"})
    s.destination_text=body.destination_text; s.status="destination_selected"; db.commit()
    return {"session_id":s.id,"destination":s.destination_text,"departure_station":s.departure_station_text,"status":s.status}
@app.post("/api/v1/sessions/{session_id}/train-search")
def train_search(session_id:str,db:Session=Depends(get_db)):
    s=db.get(ProjectSession,session_id)
    if not s: raise HTTPException(404,detail={"code":"session_not_found"})
    if not s.departure_station_text: raise HTTPException(409,detail={"code":"departure_station_required"})
    if not s.departure_date: raise HTTPException(409,detail={"code":"departure_date_required"})
    raise HTTPException(503,detail={"code":"train_source_not_configured","message":"Aucune source d’horaires actualisée n’est configurée ; aucun horaire n’est inventé."})
@app.get("/api/v1/sessions/{session_id}/summary")
def summary(session_id:str,db:Session=Depends(get_db)):
    s=db.get(ProjectSession,session_id)
    if not s: raise HTTPException(404,detail={"code":"session_not_found"})
    return {"session_id":s.id,"status":s.status,"departure_station":s.departure_station_text,
      "departure_date":s.departure_date,"student_count":s.student_count,"supervisor_count":s.supervisor_count,
      "destination":s.destination_text,"warning":"Les horaires et places ne sont pas confirmés par ce prototype."}
@app.post("/api/v1/reservation-requests")
def reservation(body:ReservationIn,db:Session=Depends(get_db)):
    if not db.get(ProjectSession,body.session_id): raise HTTPException(404,detail={"code":"session_not_found"})
    r=ReservationRequest(session_id=body.session_id,contact_name=body.contact_name,school_name=body.school_name,email=body.email,status="pending")
    db.add(r); db.commit(); db.refresh(r)
    return {"request_id":r.id,"status":"pending","message":"Demande enregistrée en attente ; ce n’est pas une réservation confirmée."}
@app.post("/api/v1/sessions/{session_id}/feedback")
def feedback(session_id:str,rating:int=Query(...,ge=1,le=5),comments:str|None=None,db:Session=Depends(get_db)):
    if not db.get(ProjectSession,session_id): raise HTTPException(404,detail={"code":"session_not_found"})
    db.add(Feedback(session_id=session_id,rating=rating,comments=comments)); db.commit()
    return {"stored":True}
