import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
def uid(): return str(uuid.uuid4())

class Accommodation(Base):
    __tablename__="accommodations"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    source_record_id: Mapped[str|None]=mapped_column(String(250),unique=True,nullable=True)
    name: Mapped[str]=mapped_column(String(300),index=True)
    commune: Mapped[str|None]=mapped_column(String(160),index=True,nullable=True)
    department: Mapped[str|None]=mapped_column(String(100),index=True,nullable=True)
    postal_code: Mapped[str|None]=mapped_column(String(20),nullable=True)
    latitude: Mapped[float|None]=mapped_column(Float,nullable=True)
    longitude: Mapped[float|None]=mapped_column(Float,nullable=True)
    themes_raw: Mapped[str|None]=mapped_column(Text,nullable=True)
    student_beds: Mapped[int|None]=mapped_column(Integer,nullable=True)
    supervisor_beds: Mapped[int|None]=mapped_column(Integer,nullable=True)
    reference_tariff: Mapped[str|None]=mapped_column(String(300),nullable=True)
    nature_label: Mapped[str|None]=mapped_column(String(100),nullable=True)
    accessible_handicap: Mapped[str|None]=mapped_column(String(100),nullable=True)
    opening_period: Mapped[str|None]=mapped_column(String(300),nullable=True)
    classrooms: Mapped[str|None]=mapped_column(String(100),nullable=True)
    coach_charter: Mapped[str|None]=mapped_column(String(100),nullable=True)
    nearby_sites_raw: Mapped[str|None]=mapped_column(Text,nullable=True)
    website_url: Mapped[str|None]=mapped_column(Text,nullable=True)
    permalink: Mapped[str|None]=mapped_column(Text,nullable=True)
    total_capacity: Mapped[int|None]=mapped_column(Integer,nullable=True)
    nearest_station_raw: Mapped[str|None]=mapped_column(String(300),nullable=True)
    straight_line_distance_km: Mapped[float|None]=mapped_column(Float,nullable=True)
    source_name: Mapped[str]=mapped_column(String(250),default="occitanie-hebergements-scolaires.xlsx")
    imported_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class ProjectSession(Base):
    __tablename__="project_sessions"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    original_request: Mapped[str|None]=mapped_column(Text,nullable=True)
    structured_request: Mapped[dict|None]=mapped_column(JSON,nullable=True)
    departure_station_text: Mapped[str|None]=mapped_column(String(250),nullable=True)
    departure_date: Mapped[str|None]=mapped_column(String(10),nullable=True)
    student_count: Mapped[int|None]=mapped_column(Integer,nullable=True)
    supervisor_count: Mapped[int|None]=mapped_column(Integer,nullable=True)
    destination_text: Mapped[str|None]=mapped_column(String(300),nullable=True)
    status: Mapped[str]=mapped_column(String(40),default="draft")
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class ConversationMessage(Base):
    __tablename__="conversation_messages"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    session_id: Mapped[str]=mapped_column(ForeignKey("project_sessions.id"),index=True)
    role: Mapped[str]=mapped_column(String(20),default="user")
    input_mode: Mapped[str]=mapped_column(String(20),default="text")
    content: Mapped[str]=mapped_column(Text)
    parsed_payload: Mapped[dict|None]=mapped_column(JSON,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class Destination(Base):
    __tablename__="destinations"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    name: Mapped[str]=mapped_column(String(300),index=True)
    commune: Mapped[str|None]=mapped_column(String(160),nullable=True)
    department: Mapped[str|None]=mapped_column(String(100),nullable=True)
    latitude: Mapped[float|None]=mapped_column(Float,nullable=True)
    longitude: Mapped[float|None]=mapped_column(Float,nullable=True)
    description: Mapped[str|None]=mapped_column(Text,nullable=True)
    source_name: Mapped[str|None]=mapped_column(String(250),nullable=True)

class TrainService(Base):
    __tablename__="train_services"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    service_code: Mapped[str|None]=mapped_column(String(100),nullable=True,index=True)
    service_date: Mapped[str|None]=mapped_column(String(10),nullable=True)
    source_name: Mapped[str|None]=mapped_column(String(250),nullable=True)
    data_status: Mapped[str]=mapped_column(String(40),default="imported_unverified")

class TrainStop(Base):
    __tablename__="train_stops"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    service_id: Mapped[str]=mapped_column(ForeignKey("train_services.id"),index=True)
    station_id: Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    stop_sequence: Mapped[int]=mapped_column(Integer)
    arrival_time: Mapped[str|None]=mapped_column(String(30),nullable=True)
    departure_time: Mapped[str|None]=mapped_column(String(30),nullable=True)

class ReservationRequest(Base):
    __tablename__="reservation_requests"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    session_id: Mapped[str]=mapped_column(ForeignKey("project_sessions.id"),index=True)
    contact_name: Mapped[str]=mapped_column(String(200))
    school_name: Mapped[str]=mapped_column(String(250))
    email: Mapped[str]=mapped_column(String(250))
    status: Mapped[str]=mapped_column(String(40),default="pending")
    submitted_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class Feedback(Base):
    __tablename__="feedback"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    session_id: Mapped[str]=mapped_column(ForeignKey("project_sessions.id"),index=True)
    rating: Mapped[int]=mapped_column(Integer)
    comments: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
