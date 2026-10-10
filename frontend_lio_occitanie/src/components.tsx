import { type ReactNode, useEffect, useRef, useState } from "react";
import { api } from "./api";
export function Heading({
  eyebrow,
  children,
}: {
  eyebrow: string;
  children: ReactNode;
}) {
  return (
    <>
      <span className="eyebrow">{eyebrow}</span>
      <h1 className="h1 title">{children}</h1>
    </>
  );
}
export function Bullet({
  icon,
  children,
}: {
  icon: string;
  children: ReactNode;
}) {
  return (
    <div className="bullet">
      <span className="icon-dot" aria-hidden="true">
        <Icon symbol={icon} />
      </span>
      <span>{children}</span>
    </div>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export function Actions({
  back,
  next,
  nextText = "Continuer →",
  disabled = false,
}: {
  back: () => void;
  next?: () => void;
  nextText?: string;
  disabled?: boolean;
}) {
  return (
    <div className="row-btns">
      <button className="btn ghost" type="button" onClick={back}>
        Retour
      </button>
      <button
        className="btn"
        type={next ? "button" : "submit"}
        onClick={next}
        disabled={disabled}
      >
        {nextText}
      </button>
    </div>
  );
}
export function VoiceInput({
  onText,
  onError,
  disabled,
}: {
  onText: (text: string) => void;
  onError: (text: string) => void;
  disabled: boolean;
}) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const active = useRef(true);
  const recordingTimeout = useRef<number | undefined>(undefined);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      window.clearTimeout(recordingTimeout.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);
  async function start() {
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)
        throw new Error(
          "Le microphone nécessite un navigateur compatible et une connexion HTTPS ou localhost. Vous pouvez saisir votre projet ci-dessous.",
        );
      const audio = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!active.current) {
        audio.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = audio;
      const mimeType = [
        "audio/webm;codecs=opus",
        "audio/mp4",
        "audio/ogg;codecs=opus",
      ].find((t) => MediaRecorder.isTypeSupported(t));
      const media = new MediaRecorder(
        audio,
        mimeType ? { mimeType } : undefined,
      );
      recorder.current = media;
      const chunks: BlobPart[] = [];
      media.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      media.onstop = async () => {
        audio.getTracks().forEach((t) => t.stop());
        window.clearTimeout(recordingTimeout.current);
        if (!active.current) return;
        setRecording(false);
        setTranscribing(true);
        try {
          const form = new FormData();
          const extension = media.mimeType.includes("mp4")
            ? "mp4"
            : media.mimeType.includes("ogg")
              ? "ogg"
              : "webm";
          form.append(
            "file",
            new Blob(chunks, { type: media.mimeType }),
            `projet.${extension}`,
          );
          form.append("language", "fr");
          const result = await api<{
            transcription: string;
            speech_detected: boolean;
          }>("/api/analyzeVoice", form);
          if (active.current) {
            if (!result.speech_detected || !result.transcription)
              throw new Error(
                "Aucune parole détectée. Réessayez ou saisissez votre projet.",
              );
            onText(result.transcription);
          }
        } catch (error) {
          if (active.current) onError((error as Error).message);
        } finally {
          if (active.current) setTranscribing(false);
        }
      };
      media.start();
      setRecording(true);
      recordingTimeout.current = window.setTimeout(() => {
        if (media.state === "recording") media.stop();
      }, 120000);
    } catch (error) {
      stream.current?.getTracks().forEach((track) => track.stop());
      onError(
        error instanceof DOMException && error.name === "NotAllowedError"
          ? "Accès au microphone refusé. Autorisez-le dans votre navigateur ou saisissez votre projet."
          : (error as Error).message,
      );
    }
  }
  return (
    <div className="voice">
      <button
        type="button"
        className={`btn ${recording ? "" : "ghost"}`}
        disabled={disabled || transcribing}
        onClick={() => (recording ? recorder.current?.stop() : void start())}
      >
        <Icon symbol={recording ? "⏹" : "🎙️"} />
        {recording
          ? "Arrêter et transcrire"
          : transcribing
            ? "Transcription en cours…"
            : "Décrire mon projet à l’oral"}
      </button>
      <p className="muted" role="status">
        {recording
          ? "Enregistrement en cours (2 minutes maximum)…"
          : "La transcription sera affichée pour vérification avant analyse."}
      </p>
    </div>
  );
}

// Inline SVGs keep the interface independent of emoji fonts and external services.
export function Icon({ symbol }: { symbol: string }) {
  const paths: Record<string, ReactNode> = {
    "📍": (
      <>
        <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" />
        <circle cx="12" cy="10" r="2.5" />
      </>
    ),
    "🚆": (
      <>
        <rect x="5" y="3" width="14" height="16" rx="4" />
        <path d="M5 10h14M12 3v7M8 19l-2 3M16 19l2 3" />
        <path d="M8 15h1M15 15h1" />
      </>
    ),
    "✅": (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m7 12 3 3 7-7" />
      </>
    ),
    "🎙️": (
      <>
        <rect x="9" y="2" width="6" height="13" rx="3" />
        <path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8" />
      </>
    ),
    "✏️": (
      <>
        <path d="m16 3 5 5-12 12-6 1 1-6Z M14 5l5 5" />
      </>
    ),
    "📘": (
      <>
        <path d="M4 4h7a3 3 0 0 1 3 3v14a4 4 0 0 0-4-2H4ZM14 7a3 3 0 0 1 3-3h4v15h-3a4 4 0 0 0-4 2" />
      </>
    ),
    "🎯": (
      <>
        <circle cx="12" cy="12" r="9" />
        <circle cx="12" cy="12" r="5" />
        <circle cx="12" cy="12" r="1" />
      </>
    ),
    "👥": (
      <>
        <circle cx="9" cy="7" r="3" />
        <path d="M2 21v-3a7 7 0 0 1 14 0v3M17 4a3 3 0 0 1 0 6M19 14a5 5 0 0 1 3 5v2" />
      </>
    ),
    "📅": (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M7 2v6M17 2v6M3 11h18M7 15h3M14 15h3" />
      </>
    ),
    "🧭": (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m16 8-3 5-5 3 3-5Z" />
      </>
    ),
    "🏁": (
      <>
        <path d="M5 22V3c5-4 9 4 14 0v11c-5 4-9-4-14 0" />
      </>
    ),
    "🚶": (
      <>
        <circle cx="14" cy="4" r="2" />
        <path d="m7 22 4-8 3 3v5M7 12l3-5 4 1 3 5h4M11 8v6" />
      </>
    ),
    "🎒": (
      <>
        <rect x="5" y="6" width="14" height="16" rx="4" />
        <path d="M9 6V4a3 3 0 0 1 6 0v2M8 14h8v5H8ZM5 10H2v8h3M19 10h3v8h-3" />
      </>
    ),
    "♿": (
      <>
        <circle cx="12" cy="3" r="2" />
        <path d="M12 7v7h6l3 6M12 10h5M8 10a6 6 0 1 0 7 9" />
      </>
    ),
    "🏫": (
      <>
        <path d="M3 22V9l9-7 9 7v13ZM9 22v-7h6v7M7 10h1M16 10h1" />
        <circle cx="12" cy="8" r="1" />
      </>
    ),
    "⏹": <rect x="5" y="5" width="14" height="14" rx="2" />,
  };
  return (
    <svg
      className="ui-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths[symbol] || paths["✅"]}
    </svg>
  );
}
