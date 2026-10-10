import { useEffect, useState } from "react";
import { searchDestinations, type Destination } from "./api";

/** Le catalogue existe uniquement en mémoire après une réponse de l’API. */
export function useDestinations(
  enabled: boolean,
  sessionId: string | null,
  theme: string,
  maxTrainMinutes: number | null,
) {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    setDestinations([]);
    setLoading(true);
    setLoaded(false);
    setError("");
    searchDestinations(
      {
        session_id: sessionId,
        themes: theme ? [theme] : [],
        max_train_minutes: maxTrainMinutes,
      },
      controller.signal,
    )
      .then((result) => {
        if (controller.signal.aborted) return;
        setDestinations(result.destinations);
        setLoaded(true);
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [enabled, sessionId, theme, maxTrainMinutes, revision]);

  return {
    destinations,
    loading: enabled && loading,
    loaded: enabled && loaded,
    error,
    reload: () => setRevision((value) => value + 1),
  };
}
