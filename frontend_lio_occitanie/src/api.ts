export interface Project {
  departure_station_text: string;
  departure_place: string;
  departure_date: string;
  return_date: string;
  class_level: string;
  student_count: number;
  supervisor_count: number;
  themes: string[];
  duration_days: number;
  destination_text: string;
  selected_destination_id: string | null;
  selected_train_number: string | null;
  selected_return_train_number: string | null;
  demo: boolean;
}
export interface Destination {
  id: string;
  name: string;
  commune: string | null;
  department: string | null;
  themes: string | null;
  nearest_station: string | null;
  capacity: number | null;
  distance_vol_oiseau_km: number | null;
  nearby_activities: string | null;
  accessibility_verdict: string;
  website: string | null;
  nature_label: string | null;
  accessible_handicap: string | null;
  reference_tariff: string | null;
  source_name: string;
  imported_at: string;
  kind: string;
  description: string;
  source_url: string;
  station_relation: string;
  closest_station: string | null;
  pedagogical_assessment: {
    score: number | null;
    maximum: number;
    coverage: number;
    status: "profile" | "theme_only" | "needs_project";
    notice: string;
    pedagogical_justification: string;
    regulatory_argument: string;
    components: {
      label: string;
      points: number;
      maximum: number;
      renseigné: boolean;
    }[];
    references: { title: string; url: string }[];
  };
}
export interface Train {
  train_number: string;
  departure_station: string;
  arrival_station: string;
  departure_time: string;
  arrival_time: string;
  duration_formatted: string;
  duration_minutes: number;
  group_capacity: {
    available_seats: number;
    max_limit: number;
    status: string;
    message: string;
  };
  confidence_indicator: {
    score: number;
    explanation: string;
    details: Record<string, number>;
  };
}
export interface TrainResponse {
  results: Train[];
  policy_notice: string;
  data_status: string;
  source_name: string;
}
export interface Analysis {
  session_id: string;
  extracted_data: {
    departure_station_text: string | null;
    departure_date: string | null;
    class_level: string | null;
    student_count: number | null;
    supervisor_count: number | null;
    destination_text: string | null;
    themes: string[];
    missing_fields: string[];
    clarification_question: string | null;
    analysis_mode: string;
    analysis_warning?: string;
    pedagogical_profile: PedagogicalProfile | null;
  };
}
export interface Summary {
  session_id: string;
  project: {
    departure_station: string;
    departure_date: string;
    students: number;
    supervisors: number;
    total_participants: number;
  };
  chosen_destination: { name: string; nearest_station: string | null };
  selected_train: string | null;
  official_disclaimer: string;
  demo: boolean;
}
export interface Reservation {
  reference_code: string;
  status: string;
  message: string;
  submitted_at: string;
}
const base = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export async function api<T>(
  path: string,
  data?: unknown,
  method = "POST",
  signal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    data instanceof FormData || path.endsWith("/analyze") ? 180000 : 30000,
  );
  try {
    const response = await fetch(`${base}${path}`, {
      method,
      signal: signal
        ? AbortSignal.any([controller.signal, signal])
        : controller.signal,
      headers:
        data instanceof FormData || data === undefined
          ? {}
          : { "Content-Type": "application/json" },
      body:
        data === undefined
          ? undefined
          : data instanceof FormData
            ? data
            : JSON.stringify(data),
    });
    const result = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = result?.detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((e: { msg: string }) => e.msg).join(" · ")
            : `L'API a retourné une erreur (${response.status}).`,
      );
    }
    return result as T;
  } catch (error) {
    if (signal?.aborted) throw error;
    if (error instanceof DOMException && error.name === "AbortError")
      throw new Error("Le serveur met trop de temps à répondre. Réessayez.");
    if (error instanceof TypeError)
      throw new Error(
        "Le service est momentanément indisponible. Réessayez dans quelques instants.",
      );
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export interface DestinationQuery {
  session_id: string | null;
  themes: string[];
  max_train_minutes: number | null;
  destination_station: string | null;
  search_mode: "station" | "theme";
  radius_km: number;
  class_level: string | null;
}

export function searchDestinations(
  query: DestinationQuery,
  signal: AbortSignal,
) {
  return api<{ count: number; destinations: Destination[] }>(
    "/api/destinations/search",
    query,
    "POST",
    signal,
  );
}

export interface PedagogicalProfile {
  contexte: {
    classe_declaree: string | null;
    cycle_officiel: string | null;
    eleves_count: number | null;
    accompagnateurs_count: number | null;
  };
  cadrage_pedagogique: {
    disciplines: string[];
    thematiques_programmes: string[];
    domaines_socle: string[];
    parcours_educatifs: string[];
  };
  objectifs_et_competences: {
    notions_cles: string[];
    competences_travaillees: string[];
    plus_value_terrain_exprimee: string | null;
  };
  dispositifs_attendus: { formats_activite: string[]; duree_projet: string };
  vecteurs_adequation: {
    mots_cles_patrimoine: string[];
    mots_cles_activites: string[];
    territoires_pertinents: string[];
  };
}

export interface WalkingRoute {
  closest_station: string | null;
  estimated_walking_minutes: number | null;
  walking_distance_m: number | null;
  status: "calculated" | "unavailable" | "missing_coordinates";
  source_url: string;
  notice: string;
  calculated_at?: string;
}
