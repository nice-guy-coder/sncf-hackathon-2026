import lioLogo from "../assets/logo_lio.png";
import trainPhoto from "../assets/train.jpeg";
import { useDestinations } from "./useDestinations";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  api,
  type Analysis,
  type Destination,
  type Project,
  type Reservation,
  type Summary,
  type Train,
  type TrainResponse,
} from "./api";
import {
  Actions,
  Bullet,
  Field,
  Heading,
  VoiceInput,
  Icon,
} from "./components";
const initialProject: Project = {
  departure_station_text: "",
  departure_place: "",
  departure_date: "",
  return_date: "",
  class_level: "",
  student_count: 1,
  supervisor_count: 0,
  themes: [],
  duration_days: 1,
  destination_text: "",
  selected_accommodation_id: null,
  selected_train_number: null,
  selected_return_train_number: null,
  demo: false,
};
const steps = [
  "accueil",
  "projet",
  "chat",
  "formulaire",
  "destination",
  "recherche",
  "suggestions",
  "detail",
  "trains",
  "recapitulatif",
  "coordonnees",
  "confirmation",
  "feedback",
  "aide",
] as const;
type Step = (typeof steps)[number];
type Message = { role: "bot" | "user"; text: string };
const storageKey = "lio-project-v1";
function loadDraft(): { project: Project; sessionId: string | null } {
  try {
    return (
      JSON.parse(sessionStorage.getItem(storageKey) || "null") || {
        project: initialProject,
        sessionId: null,
      }
    );
  } catch {
    return { project: initialProject, sessionId: null };
  }
}
function dateLabel(value: string) {
  return value
    ? new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" }).format(
        new Date(`${value}T12:00:00`),
      )
    : "Date à préciser";
}
function validStep(): Step {
  const value = location.hash.slice(1);
  return steps.includes(value as Step) ? (value as Step) : "accueil";
}
function websiteUrl(raw: string | null) {
  if (!raw) return null;
  try {
    const url = new URL(raw.startsWith("www.") ? `https://${raw}` : raw);
    return ["https:", "http:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}
export default function App() {
  const [draft] = useState(loadDraft);
  const [project, setProject] = useState<Project>({
    ...initialProject,
    ...draft.project,
  });
  const [sessionId, setSessionId] = useState<string | null>(draft.sessionId);
  const [step, setStep] = useState<Step>(validStep);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [menu, setMenu] = useState(false);
  const [input, setInput] = useState("");
  const [inputMode, setInputMode] = useState("text");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "bot",
      text: "Bonjour ! Je suis votre assistant pour organiser votre sortie scolaire en train liO. Décrivez votre classe, votre thème, les effectifs, la date et le lieu de départ.",
    },
  ]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [knownDestination, setKnownDestination] = useState(false);
  const [destination, setDestination] = useState<Destination | null>(null);
  const [theme, setTheme] = useState("");
  const [searchMode, setSearchMode] = useState("theme");
  const [maxMinutes, setMaxMinutes] = useState(120);
  const {
    destinations,
    loading: catalogLoading,
    loaded: catalogLoaded,
    error: catalogError,
    reload: reloadCatalog,
  } = useDestinations(
    step === "suggestions",
    sessionId,
    theme,
    searchMode === "duration" ? maxMinutes : null,
  );
  const [trains, setTrains] = useState<Train[]>([]);
  const [returnTrains, setReturnTrains] = useState<Train[]>([]);
  const [direction, setDirection] = useState<"outbound" | "return">("outbound");
  const [policy, setPolicy] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [reservation, setReservation] = useState<Reservation | null>(null);
  const [contact, setContact] = useState({
    contact_name: "",
    school_name: "",
    email: "",
    phone: "",
  });
  const [consent, setConsent] = useState(false);
  const [feedback, setFeedback] = useState({
    overall_rating: 5,
    punctuality_rating: 5,
    pedagogical_rating: 5,
    accessibility_rating: 5,
    comments: "",
  });
  const [feedbackSent, setFeedbackSent] = useState(false);
  const mainRef = useRef<HTMLElement>(null);
  const total = project.student_count + project.supervisor_count;
  useEffect(() => {
    try {
      sessionStorage.setItem(
        storageKey,
        JSON.stringify({ project, sessionId }),
      );
    } catch {
      /* Le parcours reste disponible si le stockage est désactivé. */
    }
  }, [project, sessionId]);
  useEffect(() => {
    function onHistory() {
      setStep(validStep());
      setError("");
      setMenu(false);
    }
    window.addEventListener("popstate", onHistory);
    window.addEventListener("hashchange", onHistory);
    return () => {
      window.removeEventListener("popstate", onHistory);
      window.removeEventListener("hashchange", onHistory);
    };
  }, []);
  useEffect(() => {
    mainRef.current?.focus();
    window.scrollTo({ top: 0 });
  }, [step]);
  function go(next: Step) {
    history.pushState({}, "", `#${next}`);
    setStep(next);
    setError("");
    setMenu(false);
  }
  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function change<K extends keyof Project>(key: K, value: Project[K]) {
    setProject((prev) => ({
      ...prev,
      [key]: value,
      selected_train_number: null,
      selected_return_train_number: null,
    }));
    setSummary(null);
    setReservation(null);
    setTrains([]);
    setReturnTrains([]);
  }
  async function saveProject(value = project) {
    let id = sessionId;
    if (!id) {
      const created = await api<{ session_id: string }>(
        "/api/v1/sessions",
        undefined,
      );
      id = created.session_id;
      setSessionId(id);
    }
    await api(
      `/api/v1/sessions/${id}`,
      {
        ...value,
        return_date: value.return_date || value.departure_date,
        destination_text: value.destination_text || null,
      },
      "PATCH",
    );
    return id;
  }
  async function analyze(event: FormEvent) {
    event.preventDefault();
    if (!input.trim()) return;
    await run(async () => {
      const text = input.trim();
      const result = await api<Analysis>("/api/trips/analyze", {
        content: text,
        input_mode: inputMode,
        session_id: sessionId,
      });
      setSessionId(result.session_id);
      setAnalysis(result);
      const data = result.extracted_data;
      setProject((prev) => ({
        ...prev,
        departure_station_text: data.departure_station_text || "",
        departure_date: data.departure_date || "",
        return_date: data.departure_date || "",
        class_level: data.class_level || "",
        student_count: data.student_count ?? 1,
        supervisor_count: data.supervisor_count ?? 0,
        themes: data.themes,
        destination_text: data.destination_text || "",
        selected_accommodation_id: null,
        selected_train_number: null,
        selected_return_train_number: null,
      }));
      setKnownDestination(Boolean(data.destination_text));
      setMessages((prev) => [
        ...prev,
        { role: "user", text },
        {
          role: "bot",
          text:
            data.clarification_question ||
            "Voici les informations extraites. Vérifiez-les avant de continuer ; la gare de départ doit être confirmée par vous.",
        },
      ]);
      setInput("");
      setInputMode("text");
    });
  }
  function loadDestinations(value = theme) {
    setTheme(value);
    if (step === "suggestions" && value === theme) reloadCatalog();
    if (step !== "suggestions") go("suggestions");
  }
  async function searchTrains(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      await saveProject();
      const body = {
        session_id: sessionId,
        departure_station: project.departure_station_text,
        destination_station: project.destination_text,
        departure_date: project.departure_date,
        return_date: project.return_date || project.departure_date,
        total_participants: total,
        demo: project.demo,
      };
      const outbound = await api<TrainResponse>("/api/trains/search", body);
      const inbound = await api<TrainResponse>("/api/trains/search", {
        ...body,
        departure_station: project.destination_text,
        destination_station: project.departure_station_text,
        departure_date: project.return_date || project.departure_date,
      });
      setTrains(outbound.results);
      setReturnTrains(inbound.results);
      setPolicy(outbound.policy_notice);
      setProject((prev) => ({
        ...prev,
        selected_train_number: null,
        selected_return_train_number: null,
      }));
      setDirection("outbound");
      go("trains");
    });
  }
  async function makeSummary() {
    await run(async () => {
      const id = await saveProject();
      const result = await api<Summary>("/api/trips/summary", {
        session_id: id,
        destination_id: project.selected_accommodation_id,
        train_number: project.selected_train_number,
      });
      setSummary(result);
      go("recapitulatif");
    });
  }
  const chosenTrain = trains.find(
    (t) => t.train_number === project.selected_train_number,
  );
  const chosenReturn = returnTrains.find(
    (t) => t.train_number === project.selected_return_train_number,
  );
  const showRecovery =
    [
      "detail",
      "trains",
      "recapitulatif",
      "coordonnees",
      "confirmation",
    ].includes(step) &&
    ((step === "detail" && !destination) ||
      (step === "trains" && !policy) ||
      (["recapitulatif", "coordonnees"].includes(step) && !summary) ||
      (step === "confirmation" && !reservation));
  return (
    <div className="page">
      <a className="skip" href="#main">
        Aller au contenu
      </a>
      <header className="topbar">
        <button
          className="logo plain"
          onClick={() => go("accueil")}
          aria-label="liO SNCF · Accueil"
        >
          <img className="mark" src={lioLogo} alt="liO" />
          SNCF
        </button>
        <button
          className="burger plain"
          aria-label="Menu"
          aria-expanded={menu}
          onClick={() => setMenu(!menu)}
        >
          <span />
          <span />
          <span />
        </button>
        <nav aria-label="Navigation principale" className={menu ? "open" : ""}>
          <button className="plain" onClick={() => go("projet")}>
            Mon projet
          </button>
          <button
            className="plain"
            onClick={() => void loadDestinations("")}
            disabled={busy}
          >
            Découvrir
          </button>
          <button className="plain" onClick={() => go("aide")}>
            Aide
          </button>
        </nav>
      </header>
      <main
        className={`content ${step === "accueil" ? "home" : ""}`}
        id="main"
        tabIndex={-1}
        ref={mainRef}
        aria-busy={busy || catalogLoading}
      >
        {error && (
          <div className="notice error" role="alert">
            {error}
            <button
              className="plain"
              aria-label="Fermer l’erreur"
              onClick={() => setError("")}
            >
              ×
            </button>
          </div>
        )}
        {busy && (
          <p role="status" className="notice">
            Traitement en cours…
          </p>
        )}
        <fieldset className="workflow" disabled={busy}>
          {showRecovery ? (
            <>
              <Heading eyebrow="Votre projet">
                Reprendre votre recherche
              </Heading>
              <p className="muted">
                Votre projet est conservé. Relancez la recherche pour retrouver
                des résultats et un récapitulatif à jour.
              </p>
              <button className="btn" onClick={() => go("formulaire")}>
                Reprendre mon projet →
              </button>
            </>
          ) : (
            <>
              {step === "accueil" && (
                <>
                  <div className="hero-ill">
                    <img
                      src={trainPhoto}
                      alt="Train liO"
                      className="hero-photo"
                    />
                  </div>
                  <Heading eyebrow="SNCF Voyageurs · liO">
                    Dessine-moi une mobilité durable
                  </Heading>
                  <p className="muted intro">
                    Votre copilote IA pour organiser une sortie scolaire en
                    train liO en Occitanie.
                  </p>
                  <div className="stack home-benefits">
                    <Bullet icon="📍">
                      Destinations adaptées à votre projet pédagogique
                    </Bullet>
                    <Bullet icon="🚆">
                      Trajets en train liO pour les groupes
                    </Bullet>
                    <Bullet icon="✅">
                      Préparation simple, fiable et rassurante
                    </Bullet>
                  </div>
                  <button className="btn" onClick={() => go("projet")}>
                    Commencer →
                  </button>
                </>
              )}
              {step === "projet" && (
                <>
                  <Heading eyebrow="Étape 1">
                    Comment souhaitez-vous décrire votre projet ?
                  </Heading>
                  <div className="grid2 options">
                    <button
                      className="option-card pink"
                      onClick={() => go("chat")}
                    >
                      <span className="icon-dot">
                        <Icon symbol="🎙️" />
                      </span>
                      <b>Parler à l’IA</b>
                      <span className="muted">
                        Je décris mon projet à l’oral, l’assistant extrait les
                        informations.
                      </span>
                    </button>
                    <button
                      className="option-card"
                      onClick={() => go("formulaire")}
                    >
                      <span className="icon-dot navy">
                        <Icon symbol="✏️" />
                      </span>
                      <b>Saisir les informations</b>
                      <span className="muted">
                        Je remplis le formulaire étape par étape.
                      </span>
                    </button>
                  </div>
                  <div className="row-btns stretch">
                    <button className="btn" onClick={() => go("chat")}>
                      Commencer à parler
                    </button>
                    <button
                      className="btn ghost"
                      onClick={() => go("formulaire")}
                    >
                      Remplir le formulaire
                    </button>
                  </div>
                  <hr className="sep" />
                  <p className="muted">
                    💬 Vous pouvez aussi dialoguer par écrit avec l’assistant à
                    tout moment.{" "}
                    <button className="text-button" onClick={() => go("chat")}>
                      Ouvrir le chat →
                    </button>
                  </p>
                </>
              )}
              {step === "chat" && (
                <>
                  <Heading eyebrow="Assistant · texte et voix">
                    Échange avec le chatbot
                  </Heading>
                  <div className="chat-col" aria-live="polite">
                    {messages.map((message, i) => (
                      <div key={i} className={`bubble ${message.role}`}>
                        {message.text}
                      </div>
                    ))}
                    {analysis && (
                      <div className="card">
                        <b>Voici ce que j’ai extrait :</b>
                        <div className="stack extracted">
                          <Bullet icon="📘">
                            Niveau : {project.class_level || "À préciser"}
                          </Bullet>
                          <Bullet icon="🎯">
                            Thème : {project.themes.join(", ") || "À préciser"}
                          </Bullet>
                          <Bullet icon="👥">
                            {analysis.extracted_data.student_count ??
                              "À préciser"}{" "}
                            élèves ·{" "}
                            {analysis.extracted_data.supervisor_count ??
                              "À préciser"}{" "}
                            accompagnateurs
                          </Bullet>
                          <Bullet icon="📅">
                            {dateLabel(project.departure_date)}
                          </Bullet>
                          <Bullet icon="📍">
                            Départ :{" "}
                            {project.departure_station_text || "À préciser"}
                          </Bullet>
                        </div>
                        <p className="muted">
                          Confirmez la gare et les informations extraites avant
                          la recherche.
                        </p>
                      </div>
                    )}
                  </div>
                  <VoiceInput
                    disabled={busy}
                    onText={(text) => {
                      setInput(text);
                      setInputMode("speech_to_text");
                    }}
                    onError={setError}
                  />
                  <form onSubmit={analyze}>
                    <Field label="Votre message">
                      <textarea
                        className="input"
                        rows={4}
                        maxLength={12000}
                        value={input}
                        onChange={(e) => {
                          setInput(e.target.value);
                          setInputMode("text");
                        }}
                        placeholder="Nous sommes 30 élèves et 3 accompagnateurs, au départ de Toulouse le 15/11/2026, sur le thème du patrimoine…"
                        required
                      />
                    </Field>
                    <button className="btn" disabled={!input.trim()}>
                      Envoyer →
                    </button>
                  </form>
                  {analysis && (
                    <Actions
                      back={() => go("formulaire")}
                      next={() => go("formulaire")}
                      nextText="Vérifier et continuer →"
                    />
                  )}
                </>
              )}
              {step === "formulaire" && (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void run(async () => {
                      await saveProject();
                      go("destination");
                    });
                  }}
                >
                  <Heading eyebrow="Votre projet">
                    Renseignez votre projet pédagogique
                  </Heading>
                  <Field label="Niveau de classe *">
                    <input
                      className="input"
                      required
                      maxLength={50}
                      value={project.class_level}
                      onChange={(e) => change("class_level", e.target.value)}
                      placeholder="5e (Collège)"
                    />
                  </Field>
                  <Field label="Thème ou objectif pédagogique *">
                    <input
                      className="input"
                      required
                      maxLength={300}
                      value={project.themes.join(", ")}
                      onChange={(e) =>
                        change(
                          "themes",
                          e.target.value
                            .split(",")
                            .map((t) => t.trim())
                            .filter(Boolean),
                        )
                      }
                      placeholder="Moyen Âge"
                    />
                  </Field>
                  <div className="grid2">
                    <Field label="Nombre d’élèves *">
                      <input
                        className="input"
                        type="number"
                        required
                        min={1}
                        max={50}
                        value={project.student_count}
                        onChange={(e) =>
                          change("student_count", Number(e.target.value))
                        }
                      />
                    </Field>
                    <Field label="Nombre d’accompagnateurs *">
                      <input
                        className="input"
                        type="number"
                        required
                        min={0}
                        max={49}
                        value={project.supervisor_count}
                        onChange={(e) =>
                          change("supervisor_count", Number(e.target.value))
                        }
                      />
                    </Field>
                  </div>
                  {total > 50 && (
                    <p className="notice error" role="alert">
                      {total} voyageurs : maximum 50 par train liO. Plusieurs
                      groupes nécessitent une organisation dédiée.
                    </p>
                  )}
                  <div className="grid2">
                    <Field label="Date précise souhaitée *">
                      <input
                        className="input"
                        required
                        type="date"
                        value={project.departure_date}
                        onChange={(e) =>
                          change("departure_date", e.target.value)
                        }
                      />
                    </Field>
                    <Field label="Durée de la sortie *">
                      <select
                        className="input"
                        value={project.duration_days}
                        onChange={(e) =>
                          change("duration_days", Number(e.target.value))
                        }
                      >
                        {[1, 2, 3, 4, 5].map((n) => (
                          <option key={n} value={n}>
                            {n} {n === 1 ? "journée" : "jours"}
                          </option>
                        ))}
                      </select>
                    </Field>
                  </div>
                  <Field label="Lieu réel de départ *">
                    <input
                      className="input"
                      required
                      maxLength={300}
                      value={project.departure_place}
                      onChange={(e) =>
                        change("departure_place", e.target.value)
                      }
                      placeholder="Collège de Foix"
                    />
                  </Field>
                  <Field label="Gare de départ à confirmer *">
                    <input
                      className="input"
                      required
                      minLength={2}
                      maxLength={250}
                      value={project.departure_station_text}
                      onChange={(e) =>
                        change("departure_station_text", e.target.value)
                      }
                      placeholder="Foix"
                    />
                  </Field>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={knownDestination}
                      onChange={(e) => setKnownDestination(e.target.checked)}
                    />
                    Je connais déjà ma destination (facultatif)
                  </label>
                  <Actions back={() => go("projet")} disabled={total > 50} />
                </form>
              )}
              {step === "destination" && (
                <>
                  <div
                    className="hero-ill destination-hero"
                    aria-hidden="true"
                  />
                  <Heading eyebrow="Étape 2">
                    Avez-vous déjà une destination en tête ?
                  </Heading>
                  <div className="grid2">
                    <button
                      className={`option-card ${knownDestination ? "pink" : ""}`}
                      aria-pressed={knownDestination}
                      onClick={() => setKnownDestination(true)}
                    >
                      <span className="icon-dot">
                        <Icon symbol="📍" />
                      </span>
                      <b>Oui</b>
                      <span className="muted">Je connais ma destination.</span>
                    </button>
                    <button
                      className={`option-card ${!knownDestination ? "pink" : ""}`}
                      aria-pressed={!knownDestination}
                      onClick={() => setKnownDestination(false)}
                    >
                      <span className="icon-dot navy">
                        <Icon symbol="🧭" />
                      </span>
                      <b>Non</b>
                      <span className="muted">
                        Je souhaite découvrir des suggestions de destinations.
                      </span>
                    </button>
                  </div>
                  <Actions
                    back={() => go("formulaire")}
                    next={() => {
                      if (knownDestination) {
                        setProject((prev) => ({
                          ...prev,
                          selected_accommodation_id: null,
                        }));
                        go("recherche");
                      } else void loadDestinations("");
                    }}
                  />
                </>
              )}
              {step === "suggestions" && (
                <>
                  <Heading eyebrow="Destination inconnue">
                    Découvrez des destinations adaptées à votre projet
                  </Heading>
                  <div className="tabs" aria-label="Mode de recherche">
                    <button
                      className={`tab plain ${searchMode === "theme" ? "on" : ""}`}
                      onClick={() => setSearchMode("theme")}
                    >
                      Par thème
                    </button>
                    <button
                      className={`tab plain ${searchMode === "duration" ? "on" : ""}`}
                      onClick={() => setSearchMode("duration")}
                    >
                      Par temps de trajet
                    </button>
                  </div>
                  {searchMode === "theme" ? (
                    <div className="chiprow">
                      {[
                        ["Tous", ""],
                        ["Histoire", "patrimoine"],
                        ["Sciences", "sciences"],
                        ["Nature", "nature"],
                        ["Culture", "culture"],
                        ["Art", "art"],
                      ].map(([label, value]) => (
                        <button
                          key={label}
                          className={`chip ${theme === value ? "on" : ""}`}
                          aria-pressed={theme === value}
                          onClick={() => void loadDestinations(value)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <>
                      <Field label="Durée maximale en train (minutes)">
                        <input
                          className="input"
                          type="number"
                          min={15}
                          max={600}
                          value={maxMinutes}
                          onChange={(e) =>
                            setMaxMinutes(Number(e.target.value))
                          }
                        />
                      </Field>
                      <p className="notice">
                        Cette contrainte ne peut pas être appliquée sans
                        horaires actualisés. Les hébergements ci-dessous ne sont
                        pas filtrés par durée.
                      </p>
                    </>
                  )}
                  <p className="muted catalog-note">
                    Découvrez les hébergements scolaires en Occitanie. Les gares
                    indiquées, les activités proches et l’accès à pied restent à
                    vérifier.
                  </p>
                  {catalogLoading && (
                    <p className="notice" role="status">
                      Recherche des lieux en cours…
                    </p>
                  )}
                  {catalogError && (
                    <div className="notice error" role="alert">
                      <div>
                        <p>Impossible de charger les lieux. {catalogError}</p>
                        <button className="btn ghost" onClick={reloadCatalog}>
                          Réessayer
                        </button>
                      </div>
                    </div>
                  )}
                  <div className="destination-grid">
                    {destinations.map((item) => (
                      <button
                        className="card destination-card"
                        key={item.id}
                        onClick={() => {
                          setDestination(item);
                          go("detail");
                        }}
                      >
                        <div className="thumb" aria-hidden="true" />
                        <div>
                          <b>{item.name}</b>
                          <span className="badge">
                            {item.commune || "Occitanie"}
                          </span>
                          <p className="muted">
                            {item.themes || "Thématiques non renseignées"}
                          </p>
                          <span className="muted">
                            {item.capacity !== null
                              ? `${item.capacity} places d’hébergement`
                              : "Capacité non renseignée"}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                  {catalogLoaded && !destinations.length && (
                    <div className="card">
                      <p>Aucun hébergement pour ce filtre.</p>
                      <button
                        className="btn ghost"
                        onClick={() => void loadDestinations("")}
                      >
                        Voir tous les hébergements
                      </button>
                    </div>
                  )}
                  <div className="row-btns">
                    <button
                      className="btn ghost"
                      onClick={() => go("destination")}
                    >
                      Retour
                    </button>
                  </div>
                </>
              )}
              {step === "detail" && destination && (
                <>
                  <div className="thumbrow" aria-hidden="true">
                    {[1, 2, 3, 4].map((n) => (
                      <div className="thumb" key={n} />
                    ))}
                  </div>
                  <Heading eyebrow="Hébergement scolaire">
                    {destination.name}
                  </Heading>
                  <span className="badge">
                    {destination.themes || "Thèmes à préciser"}
                  </span>
                  <div className="stack details">
                    <Bullet icon="📍">
                      {destination.commune} · {destination.department}
                    </Bullet>
                    <Bullet icon="🏁">
                      Gare provisoire indiquée dans la source :{" "}
                      {destination.nearest_station || "Non renseignée"}
                    </Bullet>
                    <Bullet icon="🚶">
                      {destination.distance_vol_oiseau_km !== null
                        ? `${destination.distance_vol_oiseau_km} km à vol d’oiseau ; itinéraire et temps de marche non vérifiés.`
                        : "Distance et temps de marche non renseignés."}
                    </Bullet>
                    <Bullet icon="🎒">
                      Activités à proximité :{" "}
                      {destination.nearby_activities || "Non renseignées"}
                    </Bullet>
                    <Bullet icon="👥">
                      Capacité d’hébergement :{" "}
                      {destination.capacity ?? "Non renseignée"}
                    </Bullet>
                    <Bullet icon="♿">
                      Accessibilité déclarée :{" "}
                      {destination.accessible_handicap || "Non renseignée"}
                    </Bullet>
                  </div>
                  {websiteUrl(destination.website) && (
                    <a
                      className="text-button"
                      href={websiteUrl(destination.website)!}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Consulter le site de la structure ↗
                    </a>
                  )}
                  <p className="muted source">
                    Catalogue d’hébergements scolaires · Mis à jour le{" "}
                    {new Date(destination.imported_at).toLocaleDateString(
                      "fr-FR",
                    )}
                  </p>
                  <Actions
                    back={() => go("suggestions")}
                    next={() => {
                      setProject((prev) => ({
                        ...prev,
                        selected_accommodation_id: destination.id,
                        destination_text: destination.nearest_station || "",
                        selected_train_number: null,
                        selected_return_train_number: null,
                      }));
                      go("recherche");
                    }}
                    nextText="Voir les trains pour cette destination →"
                  />
                </>
              )}
              {step === "recherche" && (
                <form onSubmit={searchTrains}>
                  <Heading eyebrow="Votre destination">
                    Recherchez les trains pour votre destination
                  </Heading>
                  <div className="grid2">
                    <Field label="Départ · gare confirmée *">
                      <input
                        className="input"
                        required
                        minLength={2}
                        maxLength={250}
                        value={project.departure_station_text}
                        onChange={(e) =>
                          change("departure_station_text", e.target.value)
                        }
                      />
                    </Field>
                    <Field label="Arrivée · gare à confirmer *">
                      <input
                        className="input"
                        required
                        minLength={2}
                        maxLength={300}
                        value={project.destination_text}
                        onChange={(e) =>
                          change("destination_text", e.target.value)
                        }
                        placeholder="Carcassonne"
                      />
                    </Field>
                  </div>
                  <div className="grid2">
                    <Field label="Date aller *">
                      <input
                        className="input"
                        required
                        type="date"
                        value={project.departure_date}
                        onChange={(e) =>
                          change("departure_date", e.target.value)
                        }
                      />
                    </Field>
                    <Field label="Date retour *">
                      <input
                        className="input"
                        required
                        min={project.departure_date}
                        type="date"
                        value={project.return_date || project.departure_date}
                        onChange={(e) => change("return_date", e.target.value)}
                      />
                    </Field>
                  </div>
                  <Field label="Nombre de personnes">
                    <input className="input" readOnly value={total} />
                  </Field>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={project.demo}
                      onChange={(e) => change("demo", e.target.checked)}
                    />
                    Consulter la démonstration historique (horaires et jauges
                    non confirmés).
                  </label>
                  <p className="muted">
                    Aucune source d’horaires actualisés ni de disponibilités
                    groupes n’est connectée. La démonstration utilise une
                    journée type du fichier fourni.
                  </p>
                  <button className="btn block" disabled={total > 50}>
                    Rechercher les trains
                  </button>
                  <div className="row-btns">
                    <button
                      className="btn ghost"
                      type="button"
                      onClick={() => go("destination")}
                    >
                      Retour
                    </button>
                    {project.destination_text && (
                      <button
                        className="btn ghost"
                        type="button"
                        onClick={() => void makeSummary()}
                      >
                        Préparer le dossier sans train confirmé
                      </button>
                    )}
                  </div>
                </form>
              )}
              {step === "trains" && (
                <>
                  <Heading
                    eyebrow={`${project.destination_text} · ${dateLabel(project.departure_date)}`}
                  >
                    Trains disponibles pour {project.destination_text}
                  </Heading>
                  <p className="notice">{policy}</p>
                  <div className="tabs">
                    <button
                      className={`tab plain ${direction === "outbound" ? "on" : ""}`}
                      onClick={() => setDirection("outbound")}
                    >
                      Aller ·{" "}
                      {project.selected_train_number ? "✓" : "À choisir"}
                    </button>
                    <button
                      className={`tab plain ${direction === "return" ? "on" : ""}`}
                      onClick={() => setDirection("return")}
                    >
                      Retour ·{" "}
                      {project.selected_return_train_number ? "✓" : "À choisir"}
                    </button>
                  </div>
                  {(direction === "outbound" ? trains : returnTrains).map(
                    (train) => {
                      const selected =
                        (direction === "outbound"
                          ? project.selected_train_number
                          : project.selected_return_train_number) ===
                        train.train_number;
                      const insufficient =
                        train.group_capacity.status === "insufficient";
                      const earlyReturn =
                        direction === "return" &&
                        Boolean(chosenTrain) &&
                        (project.return_date || project.departure_date) ===
                          project.departure_date &&
                        train.departure_time <= chosenTrain!.arrival_time;
                      return (
                        <article
                          key={`${direction}-${train.train_number}`}
                          className={`train-card ${selected ? "active" : ""}`}
                        >
                          <div>
                            <b>
                              {train.departure_time} → {train.arrival_time}
                            </b>
                            <br />
                            <span className="muted">
                              {train.duration_formatted} · Direct · liO n°{" "}
                              {train.train_number}
                            </span>
                          </div>
                          <div>
                            <span
                              className={`avail ${insufficient ? "insufficient" : ""}`}
                            >
                              {train.group_capacity.available_seats} / 50 ·
                              Jauge simulée
                            </span>
                            <details className="confidence">
                              <summary>
                                Confiance de démonstration :{" "}
                                {train.confidence_indicator.score}/100
                              </summary>
                              <p>{train.confidence_indicator.explanation}</p>
                              {Object.entries(
                                train.confidence_indicator.details,
                              ).map(([key, value]) => (
                                <p key={key}>
                                  {
                                    {
                                      regularity_pts: "Régularité",
                                      reliability_pts: "Fiabilité",
                                      accessibility_pts: "Accès simulé",
                                      capacity_pts: "Capacité simulée",
                                    }[key]
                                  }{" "}
                                  : {value} points
                                </p>
                              ))}
                            </details>
                          </div>
                          <button
                            className={`btn ${selected ? "" : "ghost"}`}
                            disabled={insufficient || earlyReturn}
                            aria-pressed={selected}
                            onClick={() =>
                              setProject((prev) => ({
                                ...prev,
                                [direction === "outbound"
                                  ? "selected_train_number"
                                  : "selected_return_train_number"]:
                                  train.train_number,
                                ...(direction === "outbound"
                                  ? { selected_return_train_number: null }
                                  : {}),
                              }))
                            }
                          >
                            {insufficient
                              ? "Groupe trop grand"
                              : earlyReturn
                                ? "Retour trop tôt"
                                : selected
                                  ? "Sélectionné ✓"
                                  : "Sélectionner"}
                          </button>
                        </article>
                      );
                    },
                  )}
                  {!(direction === "outbound" ? trains : returnTrains)
                    .length && (
                    <p className="card">
                      Aucune liaison directe dans la journée type pour ce
                      trajet. Les correspondances ne sont pas encore calculées.
                    </p>
                  )}
                  <Actions
                    back={() => go("recherche")}
                    next={() => void makeSummary()}
                    disabled={
                      !project.selected_train_number ||
                      !project.selected_return_train_number
                    }
                  />
                  <button
                    className="text-button secondary-action"
                    onClick={() => {
                      setProject((prev) => ({
                        ...prev,
                        selected_train_number: null,
                        selected_return_train_number: null,
                      }));
                      go("recherche");
                    }}
                  >
                    Modifier les gares ou préparer un dossier sans train
                  </button>
                </>
              )}
              {step === "recapitulatif" && summary && (
                <>
                  <span className="eyebrow">Récapitulatif de votre projet</span>
                  <div className="grid2 recap">
                    <div className="thumb" aria-hidden="true" />
                    <div>
                      <h1 className="h3">
                        {summary.chosen_destination.name ||
                          project.destination_text}
                      </h1>
                      <p className="muted">
                        {dateLabel(project.departure_date)} ·{" "}
                        {project.duration_days}{" "}
                        {project.duration_days === 1 ? "journée" : "jours"}
                      </p>
                      <div className="stack">
                        <Bullet icon="👥">
                          {summary.project.students} élèves +{" "}
                          {summary.project.supervisors} accompagnateurs (
                          {summary.project.total_participants} personnes)
                        </Bullet>
                        <Bullet icon="🏫">
                          {project.departure_place ||
                            summary.project.departure_station}
                        </Bullet>
                        <Bullet icon="🚆">
                          {chosenTrain
                            ? `Aller : ${chosenTrain.departure_time} → ${chosenTrain.arrival_time} · n° ${chosenTrain.train_number}`
                            : "Aller non confirmé"}
                          <br />
                          {chosenReturn
                            ? `Retour : ${chosenReturn.departure_time} → ${chosenReturn.arrival_time} · n° ${chosenReturn.train_number}`
                            : "Retour non confirmé"}
                        </Bullet>
                        <Bullet icon="🚶">Accès gare → site non vérifié</Bullet>
                      </div>
                    </div>
                  </div>
                  <p className="notice">
                    {summary.demo
                      ? "Horaires historiques et jauges simulées. "
                      : ""}
                    {summary.official_disclaimer}
                  </p>
                  <div className="row-btns">
                    <button
                      className="btn ghost"
                      onClick={() => go("formulaire")}
                    >
                      Modifier
                    </button>
                    <button className="btn" onClick={() => go("coordonnees")}>
                      Continuer →
                    </button>
                  </div>
                </>
              )}
              {step === "coordonnees" && (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void run(async () => {
                      if (!sessionId || !consent) return;
                      const result = await api<Reservation>(
                        "/api/prereservations",
                        {
                          ...contact,
                          session_id: sessionId,
                          phone: contact.phone || null,
                        },
                      );
                      setReservation(result);
                      go("confirmation");
                    });
                  }}
                >
                  <Heading eyebrow="Dernière étape">Vos coordonnées</Heading>
                  {(
                    [
                      ["contact_name", "Nom *", "text"],
                      ["school_name", "Établissement scolaire *", "text"],
                      ["email", "Email *", "email"],
                      ["phone", "Téléphone (facultatif)", "tel"],
                    ] as const
                  ).map(([key, label, type]) => (
                    <Field key={key} label={label}>
                      <input
                        className="input"
                        type={type}
                        required={key !== "phone"}
                        minLength={
                          key === "email" ? 5 : key === "phone" ? undefined : 2
                        }
                        maxLength={key === "phone" ? 50 : 200}
                        autoComplete={
                          {
                            contact_name: "name",
                            school_name: "organization",
                            email: "email",
                            phone: "tel",
                          }[key]
                        }
                        value={contact[key]}
                        onChange={(e) =>
                          setContact((prev) => ({
                            ...prev,
                            [key]: e.target.value,
                          }))
                        }
                      />
                    </Field>
                  ))}
                  <label className="check">
                    <input
                      type="checkbox"
                      required
                      checked={consent}
                      onChange={(e) => setConsent(e.target.checked)}
                    />
                    Je comprends que cette demande est enregistrée dans le
                    prototype, en attente de validation. Aucun billet, email ou
                    envoi à SNCF liO n’est généré.
                  </label>
                  <Actions
                    back={() => go("recapitulatif")}
                    nextText="Envoyer ma demande de pré-réservation →"
                    disabled={!consent || Boolean(reservation)}
                  />
                </form>
              )}
              {step === "confirmation" && reservation && (
                <>
                  <Heading eyebrow="Demande enregistrée">
                    Votre dossier est en attente
                  </Heading>
                  <div className="card">
                    <span className="badge">En attente</span>
                    <p className="reference">{reservation.reference_code}</p>
                    <p>{reservation.message}</p>
                    <p className="muted">
                      Enregistré le{" "}
                      {new Date(reservation.submitted_at).toLocaleString(
                        "fr-FR",
                      )}
                    </p>
                  </div>
                  <p className="notice">
                    Cette référence identifie une demande locale. Elle ne
                    confirme aucune réservation.
                  </p>
                  <div className="row-btns">
                    <button
                      className="btn ghost"
                      onClick={() => window.print()}
                    >
                      Imprimer le récapitulatif
                    </button>
                    <button className="btn" onClick={() => go("feedback")}>
                      Partager un retour d’expérience →
                    </button>
                  </div>
                  <div className="print-summary">
                    <h2>{project.destination_text}</h2>
                    <p>
                      {dateLabel(project.departure_date)} · {total} voyageurs ·
                      Départ : {project.departure_station_text}
                    </p>
                    <p>
                      Aller : {project.selected_train_number || "Non confirmé"}{" "}
                      · Retour :{" "}
                      {project.selected_return_train_number || "Non confirmé"}
                    </p>
                  </div>
                </>
              )}
              {step === "feedback" && (
                <>
                  <Heading eyebrow="Après votre sortie">
                    Votre retour d’expérience
                  </Heading>
                  {feedbackSent ? (
                    <div role="status" className="card">
                      <h2 className="h3">Merci pour votre retour !</h2>
                      <p>
                        Votre avis a été enregistré. L’agrégation des avis dans
                        l’indicateur reste à développer.
                      </p>
                      <button className="btn" onClick={() => go("accueil")}>
                        Retour à l’accueil
                      </button>
                    </div>
                  ) : (
                    <form
                      onSubmit={(event) => {
                        event.preventDefault();
                        void run(async () => {
                          await api("/api/feedback", {
                            ...feedback,
                            session_id: sessionId,
                          });
                          setFeedbackSent(true);
                        });
                      }}
                    >
                      <p className="muted">
                        À compléter après le voyage. Les notes vont de 1
                        (insatisfaisant) à 5 (très satisfait).
                      </p>
                      {(
                        [
                          ["overall_rating", "Satisfaction globale"],
                          ["punctuality_rating", "Ponctualité"],
                          ["pedagogical_rating", "Intérêt pédagogique"],
                          ["accessibility_rating", "Accessibilité gare → site"],
                        ] as const
                      ).map(([key, label]) => (
                        <Field key={key} label={label}>
                          <select
                            className="input"
                            value={feedback[key]}
                            onChange={(e) =>
                              setFeedback((prev) => ({
                                ...prev,
                                [key]: Number(e.target.value),
                              }))
                            }
                          >
                            {[1, 2, 3, 4, 5].map((n) => (
                              <option key={n} value={n}>
                                {n} / 5
                              </option>
                            ))}
                          </select>
                        </Field>
                      ))}
                      <Field label="Votre commentaire (facultatif)">
                        <textarea
                          className="input"
                          rows={4}
                          maxLength={4000}
                          value={feedback.comments}
                          onChange={(e) =>
                            setFeedback((prev) => ({
                              ...prev,
                              comments: e.target.value,
                            }))
                          }
                        />
                      </Field>
                      <button className="btn">Enregistrer mon retour →</button>
                    </form>
                  )}
                </>
              )}
              {step === "aide" && (
                <>
                  <Heading eyebrow="Copilote liO">
                    Préparer votre sortie en confiance
                  </Heading>
                  <div className="stack">
                    <div className="card">
                      <h2 className="h3">Décrire votre projet</h2>
                      <p>
                        Utilisez le chat, le micro ou le formulaire. Confirmez
                        la gare de départ, la date et les effectifs. Un groupe
                        est limité à 50 voyageurs par train.
                      </p>
                    </div>
                    <div className="card">
                      <h2 className="h3">Comprendre les données</h2>
                      <p>
                        Les suggestions présentent des hébergements scolaires en
                        Occitanie. Les distances sont à vol d’oiseau. La
                        recherche historique est une démonstration : dates de
                        circulation, places réelles, autorisations groupes et
                        accès restent à vérifier.
                      </p>
                    </div>
                    <div className="card">
                      <h2 className="h3">Pré-réserver</h2>
                      <p>
                        Les demandes sont conservées dans le prototype. Une
                        confirmation officielle nécessite une connexion au
                        service SNCF liO. Aucun email n’est envoyé.
                      </p>
                    </div>
                  </div>
                  <div className="row-btns">
                    <button className="btn" onClick={() => go("projet")}>
                      Commencer mon projet →
                    </button>
                  </div>
                </>
              )}
            </>
          )}
        </fieldset>
      </main>
    </div>
  );
}
