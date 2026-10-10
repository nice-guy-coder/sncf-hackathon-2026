-- Tables additionnelles du schéma cible. Les tables MVP sont créées par les modèles SQLAlchemy.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS themes (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL UNIQUE,
 normalized_key TEXT NOT NULL UNIQUE, description TEXT
);
CREATE TABLE IF NOT EXISTS destination_themes (
 destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
 theme_id UUID NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
 relevance_score NUMERIC, source_note TEXT, PRIMARY KEY(destination_id,theme_id)
);
CREATE TABLE IF NOT EXISTS destination_station_access (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 destination_id UUID NOT NULL REFERENCES destinations(id),
 station_id UUID NOT NULL REFERENCES stations(id),
 distance_km DOUBLE PRECISION, duration_minutes INTEGER,
 distance_type TEXT NOT NULL DEFAULT 'unknown', mode TEXT,
 confidence TEXT NOT NULL DEFAULT 'unverified', source_name TEXT
);
CREATE TABLE IF NOT EXISTS service_reliability (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 service_code TEXT, station_id UUID REFERENCES stations(id),
 observation_period DATERANGE, on_time_rate NUMERIC, delay_stats JSONB,
 cancellation_rate NUMERIC, incident_count INTEGER, source_name TEXT,
 imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS itineraries (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 session_id UUID NOT NULL REFERENCES project_sessions(id) ON DELETE CASCADE,
 destination_id UUID REFERENCES destinations(id),
 departure_station_id UUID REFERENCES stations(id), arrival_station_id UUID REFERENCES stations(id),
 departure_datetime TIMESTAMPTZ, arrival_datetime TIMESTAMPTZ, transfer_count INTEGER,
 total_train_minutes INTEGER, source_status TEXT NOT NULL DEFAULT 'unverified',
 confidence_score NUMERIC, warnings JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE TABLE IF NOT EXISTS itinerary_legs (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 itinerary_id UUID NOT NULL REFERENCES itineraries(id) ON DELETE CASCADE,
 sequence INTEGER NOT NULL, service_id UUID REFERENCES train_services(id),
 from_station_id UUID REFERENCES stations(id), to_station_id UUID REFERENCES stations(id),
 departure_datetime TIMESTAMPTZ, arrival_datetime TIMESTAMPTZ,
 leg_status TEXT NOT NULL DEFAULT 'unverified', UNIQUE(itinerary_id,sequence)
);
CREATE TABLE IF NOT EXISTS status_history (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 reservation_request_id UUID NOT NULL REFERENCES reservation_requests(id) ON DELETE CASCADE,
 old_status TEXT, new_status TEXT NOT NULL, changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 changed_by TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS stations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    uic_code TEXT UNIQUE,
    commune TEXT,
    department TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source_name TEXT,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_accommodation_place ON accommodations(department,commune);
CREATE INDEX IF NOT EXISTS idx_messages_session ON conversation_messages(session_id,created_at);
CREATE INDEX IF NOT EXISTS idx_train_stops_station ON train_stops(station_id);
