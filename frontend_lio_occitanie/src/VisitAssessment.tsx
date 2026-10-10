import { useEffect, useState } from "react";
import { api, type Destination, type WalkingRoute } from "./api";

const walkingCache = new Map<string, WalkingRoute>();
export function WalkingInfo({ destination }: { destination: Destination }) {
  const [route, setRoute] = useState<WalkingRoute | null>(
    walkingCache.get(destination.id) || null,
  );
  const [error, setError] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const cached = walkingCache.get(destination.id);
    setRoute(cached || null);
    setError(false);
    if (cached) return;
    const controller = new AbortController();
    api<WalkingRoute>(
      `/api/destinations/${encodeURIComponent(destination.id)}/walking`,
      undefined,
      "GET",
      controller.signal,
    )
      .then((result) => {
        if (result.status !== "unavailable")
          walkingCache.set(destination.id, result);
        if (!controller.signal.aborted) setRoute(result);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [destination.id, revision]);
  const station = route?.closest_station || destination.closest_station;
  return (
    <div className="walking-info" aria-live="polite">
      <p>
        <strong>Gare la plus proche : </strong>
        {station || "Non déterminée"}
      </p>
      <p>
        {route?.estimated_walking_minutes != null ? (
          <>
            <strong>{route.estimated_walking_minutes} min à pied</strong>{" "}
            environ ·{" "}
            {((route.walking_distance_m || 0) / 1000).toLocaleString("fr-FR", {
              maximumFractionDigits: 2,
            })}{" "}
            km sur l’itinéraire
          </>
        ) : error ? (
          "Temps de marche indisponible."
        ) : route ? (
          route.notice
        ) : (
          "Calcul du trajet à pied…"
        )}
      </p>
      {route?.estimated_walking_minutes != null && (
        <>
          <p className="muted">{route.notice}</p>
          <a href={route.source_url} target="_blank" rel="noopener noreferrer">
            Source du calcul : IGN
          </a>
          {route.calculated_at && (
            <span className="muted">
              {" "}
              · Calcul du{" "}
              {new Date(route.calculated_at).toLocaleDateString("fr-FR")}
            </span>
          )}
        </>
      )}
      {(error || route?.status === "unavailable") && (
        <button
          className="btn ghost"
          type="button"
          onClick={() => setRevision((value) => value + 1)}
        >
          Réessayer le calcul à pied
        </button>
      )}
      {station && station !== destination.nearest_station && (
        <p className="muted">
          La gare utilisée pour votre recherche est{" "}
          {destination.nearest_station}.
        </p>
      )}
    </div>
  );
}

export function VisitAssessment({ destination }: { destination: Destination }) {
  const assessment = destination.pedagogical_assessment;
  if (!assessment) return null;
  return (
    <section
      className="visit-assessment"
      aria-label={`Adéquation pédagogique de ${destination.name}`}
    >
      <p className="adequacy-score">
        <strong>
          {assessment.score === null
            ? "Adéquation à préciser"
            : `${assessment.score}/100 · Adéquation pédagogique`}
        </strong>
      </p>
      {assessment.score !== null && (
        <progress
          max={100}
          value={assessment.score}
          aria-label={`Score d’adéquation de ${destination.name}`}
        />
      )}
      <p className="muted">
        {assessment.status === "theme_only"
          ? "Évaluation partielle : thème uniquement."
          : assessment.status === "needs_project"
            ? "Précisez le thème et les objectifs de votre classe."
            : `Critères renseignés : ${assessment.coverage}/100.`}
      </p>
      <h3>Intérêt pédagogique</h3>
      <p>{assessment.pedagogical_justification}</p>
      <details open className="regulatory-argument">
        <summary>Argumentaire réglementaire</summary>
        <p>{assessment.regulatory_argument}</p>
        <div className="reference-links">
          {assessment.references.map((reference) => (
            <a
              key={reference.url}
              href={reference.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {reference.title}
            </a>
          ))}
        </div>
      </details>
      <details className="score-details">
        <summary>Comprendre le score</summary>
        <ul>
          {assessment.components.map((component) => (
            <li key={component.label}>
              {component.label} :{" "}
              {component["renseigné"]
                ? `${component.points}/${component.maximum}`
                : "critère non renseigné"}
            </li>
          ))}
        </ul>
        <p className="muted">{assessment.notice}</p>
      </details>
    </section>
  );
}
