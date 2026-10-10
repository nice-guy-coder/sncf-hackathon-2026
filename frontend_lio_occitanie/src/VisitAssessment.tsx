import { useEffect, useState } from "react";
import { api, type Destination, type WalkingRoute } from "./api";

type Assessment = Destination["pedagogical_assessment"];
const assessmentRequests = new Map<string, Promise<Assessment>>();
let assessmentQueue: Promise<unknown> = Promise.resolve();
function requestAssessment(destination: Destination) {
  const key = JSON.stringify([destination.id, destination.assessment_context]);
  const existing = assessmentRequests.get(key);
  if (existing) return existing;
  const task = assessmentQueue
    .catch(() => undefined)
    .then(() =>
      api<Assessment>(
        `/api/destinations/${encodeURIComponent(destination.id)}/assessment`,
        destination.assessment_context,
      ),
    );
  assessmentQueue = task.catch(() => undefined);
  assessmentRequests.set(key, task);
  task.then(
    (result) => {
      if (result.evaluation_mode !== "web_llm") assessmentRequests.delete(key);
    },
    () => assessmentRequests.delete(key),
  );
  return task;
}

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
  const [assessment, setAssessment] = useState(
    destination.pedagogical_assessment,
  );
  const [pending, setPending] = useState(false);
  const [revision, setRevision] = useState(0);
  const contextKey = JSON.stringify(destination.assessment_context);
  useEffect(() => {
    setAssessment(destination.pedagogical_assessment);
    if (!destination.assessment_context) return;
    const controller = new AbortController();
    setPending(true);
    requestAssessment(destination)
      .then((result) => {
        if (!controller.signal.aborted) setAssessment(result);
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setAssessment({
            ...destination.pedagogical_assessment,
            evaluation_mode: "rules_fallback",
            web_notice:
              "Analyse Web/LLM indisponible. Évaluation provisoire du catalogue.",
          });
      })
      .finally(() => {
        if (!controller.signal.aborted) setPending(false);
      });
    return () => controller.abort();
  }, [destination.id, contextKey, revision]);
  if (!assessment) return null;
  return (
    <section
      className="visit-assessment"
      aria-label={`Adéquation pédagogique de ${destination.name}`}
    >
      {pending && (
        <p role="status">
          Recherche des sources et analyse pédagogique en cours…
        </p>
      )}
      {!pending && assessment.evaluation_mode === "web_llm" && (
        <p className="muted">
          Analyse du LLM local à partir des sources Web ·{" "}
          {assessment.evaluated_at &&
            new Date(assessment.evaluated_at).toLocaleDateString("fr-FR")}
        </p>
      )}
      {!pending && assessment.evaluation_mode === "rules_fallback" && (
        <div>
          <p className="muted">{assessment.web_notice}</p>
          <button
            className="btn ghost"
            onClick={() => setRevision((value) => value + 1)}
          >
            Réessayer l’analyse pédagogique
          </button>
        </div>
      )}
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
      {!!assessment.uncertainties?.length && (
        <div>
          <h3>Informations à confirmer</h3>
          <ul>
            {assessment.uncertainties.map((value) => (
              <li key={value}>{value}</li>
            ))}
          </ul>
        </div>
      )}
      <details className="score-details">
        <summary>Comprendre le score</summary>
        <ul>
          {assessment.components.map((component) => (
            <li key={component.label}>
              {component.label} :{" "}
              {component["renseigné"]
                ? `${component.points}/${component.maximum}`
                : "critère non renseigné"}
              {component.justification && <p>{component.justification}</p>}
            </li>
          ))}
        </ul>
        <p className="muted">{assessment.notice}</p>
      </details>
    </section>
  );
}
