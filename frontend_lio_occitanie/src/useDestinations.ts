import { useEffect, useState } from "react";
import { searchDestinations, type Destination } from "./api";

/** Le catalogue existe uniquement en mémoire après une réponse de l’API. */
export function useDestinations(
  enabled: boolean,
  sessionId: string | null,
  theme: string,
  destinationStation: string | null,
  radiusKm: number,
  classLevel: string,
) {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    if (!destinationStation && !theme) {
      setDestinations([]);
      setLoaded(false);
      setLoading(false);
      setError("");
      return;
    }
    const controller = new AbortController();
    setDestinations([]);
    setLoading(true);
    setLoaded(false);
    setError("");
    searchDestinations(
      {
        session_id: sessionId,
        themes: theme ? [theme] : [],
        max_train_minutes: null,
        radius_km: radiusKm,
        class_level: classLevel || null,
        destination_station: destinationStation,
        search_mode: destinationStation ? "station" : "theme",
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
  }, [
    enabled,
    sessionId,
    theme,
    destinationStation,
    radiusKm,
    classLevel,
    revision,
  ]);

  return {
    destinations,
    loading: enabled && loading,
    loaded: enabled && loaded,
    error,
    reload: () => setRevision((value) => value + 1),
  };
}
