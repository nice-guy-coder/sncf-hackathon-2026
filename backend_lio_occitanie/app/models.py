from sqlalchemy import UniqueConstraint


class ReservationRequest(Base):
    __tablename__ = "reservation_requests"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("project_sessions.id"),
        index=True
    )

    itinerary_id: Mapped[str | None] = mapped_column(
        ForeignKey("itineraries.id"),
        nullable=True
    )

    contact_name: Mapped[str] = mapped_column(String(200))

    school_name: Mapped[str] = mapped_column(String(250))

    email: Mapped[str] = mapped_column(String(250))

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default="pending"
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid
    )

    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True
    )

    normalized_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )


class DestinationTheme(Base):
    __tablename__ = "destination_themes"

    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destinations.id"),
        primary_key=True
    )

    theme_id: Mapped[str] = mapped_column(
        ForeignKey("themes.id"),
        primary_key=True
    )

    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    source_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )


class DestinationStationAccess(Base):
    __tablename__ = "destination_station_access"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid
    )

    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destinations.id"),
        index=True
    )

    station_id: Mapped[str] = mapped_column(
        ForeignKey("stations.id"),
        index=True
    )

    distance_km: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    distance_type: Mapped[str] = mapped_column(
        String(50),
        default="unknown"
    )

    mode: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    confidence: Mapped[str] = mapped_column(
        String(50),
        default="unverified"
    )

    source_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )


class ServiceReliability(Base):
    __tablename__ = "service_reliability"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid
    )

    service_code: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True
    )

    station_id: Mapped[str | None] = mapped_column(
        ForeignKey("stations.id"),
        nullable=True
    )

    observation_period: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    on_time_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    delay_stats: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    cancellation_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    incident_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    source_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    imported_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class Itinerary(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("project_sessions.id"),
        index=True
    )

    destination_id: Mapped[str | None] = mapped_column(
        ForeignKey("destinations.id"),
        nullable=True
    )

    departure_station_id: Mapped[str | None] = mapped_column(
        ForeignKey("stations.id"),
        nullable=True
    )

    arrival_station_id: Mapped[str | None] = mapped_column(
        ForeignKey("stations.id"),
        nullable=True
    )

    departure_datetime: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    arrival_datetime: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    transfer_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    total_train_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    source_status: Mapped[str] = mapped_column(
        String(50),
        default="unverified"
    )

    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    warnings: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False
    )


class ItineraryLeg(Base):
    __tablename__ = "itinerary_legs"

    __table_args__ = (
        UniqueConstraint(
            "itinerary_id",
            "sequence",
            name="uq_itinerary_leg_sequence"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid
    )

    itinerary_id: Mapped[str] = mapped_column(
        ForeignKey("itineraries.id"),
        index=True
    )

    sequence: Mapped[int] = mapped_column(Integer)

    service_id: Mapped[str | None] = mapped_column(
        ForeignKey("train_services.id"),
        nullable=True
    )

    from_station_id: Mapped[str | None] = mapped_column(
        ForeignKey("stations.id"),
        nullable=True
    )

    to_station_id: Mapped[str | None] = mapped_column(
        ForeignKey("stations.id"),
        nullable=True
    )

    departure_datetime: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    arrival_datetime: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    leg_status: Mapped[str] = mapped_column(
        String(50),
        default="unverified"
    )


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid
    )

    reservation_request_id: Mapped[str] = mapped_column(
        ForeignKey("reservation_requests.id"),
        index=True
    )

    old_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    new_status: Mapped[str] = mapped_column(
        String(50)
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    changed_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )