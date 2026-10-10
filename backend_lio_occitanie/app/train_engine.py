import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

SCHEDULES_FILE = Path(__file__).resolve().parent.parent / "data" / "lio_train_schedules.json"

_SCHEDULES: List[Dict[str, Any]] = []

def _normalize_station_name(name: str) -> str:
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r"^(gare de|gare d'|gare du|gare des)\s+", "", n)
    n = n.replace("-", " ").replace(" saint ", " st ")
    n = n.replace("matabiau", "").replace("saint roch", "").replace("ville bourbon", "").replace("ville", "")
    return n.strip()

def get_schedules() -> List[Dict[str, Any]]:
    global _SCHEDULES
    if not _SCHEDULES and SCHEDULES_FILE.exists():
        with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
            _SCHEDULES = json.load(f)
    return _SCHEDULES

def calculate_confidence_score(
    regularity_rate: float,
    cancellation_rate: float,
    walking_minutes: int,
    available_seats: int,
    requested_pax: int
) -> Dict[str, Any]:
    """
    Calcule l'Indicateur transparent 'Confiance Voyageur Scolaire' sur 100 :
    - Régularité historique du train : 40 points
    - Absence de suppressions : 30 points
    - Accessibilité gare -> site (<= 20 min) : 15 points
    - Capacité groupe adaptée : 15 points
    """
    # 1. Régularité (40 pts)
    reg_score = min(40.0, max(0.0, (regularity_rate / 100.0) * 40.0))

    # 2. Non-suppression (30 pts)
    non_supp_rate = max(0.0, 100.0 - cancellation_rate)
    supp_score = min(30.0, max(0.0, (non_supp_rate / 100.0) * 30.0))

    # 3. Accessibilité (15 pts)
    if walking_minutes <= 20:
        access_score = 15.0
        access_label = "🟢 Accès privilégié (≤ 20 min à pied)"
    elif walking_minutes <= 35:
        access_score = 10.0
        access_label = "🟡 Accès en transport urbain ou marche modérée"
    else:
        access_score = 4.0
        access_label = "⚠️ Distance importante (> 35 min) — prévoir navette dédiée"

    # 4. Capacité groupe (15 pts)
    if requested_pax <= available_seats:
        cap_score = 15.0
        cap_label = f"🟢 Places suffisantes ({available_seats} dispo pour {requested_pax} pax)"
    else:
        cap_score = 0.0
        cap_label = f"🔴 Capacité insuffisante ({available_seats} places dispo pour {requested_pax} pax)"

    total = int(round(reg_score + supp_score + access_score + cap_score))
    total = max(10, min(100, total))

    explanation = (
        f"Train liO avec {regularity_rate:.1f}% de ponctualité, {cancellation_rate:.1f}% de suppressions. "
        f"{access_label}. {cap_label}."
    )

    return {
        "score": total,
        "max": 100,
        "explanation": explanation,
        "details": {
            "regularity_pts": round(reg_score, 1),
            "reliability_pts": round(supp_score, 1),
            "accessibility_pts": round(access_score, 1),
            "capacity_pts": round(cap_score, 1)
        }
    }

def find_train_options(
    origin: str,
    destination_station: str,
    requested_pax: int = 30,
    walking_minutes: int = 15,
    max_duration_minutes: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Recherche les circulations liO directes et calcule pour chacune la jauge et l'indice de confiance.
    """
    schedules = get_schedules()
    norm_origin = _normalize_station_name(origin)
    norm_dest = _normalize_station_name(destination_station)

    results = []
    for item in schedules:
        sched_orig = _normalize_station_name(item["origin"])
        sched_dest = _normalize_station_name(item["destination"])

        # Correspondance exacte ou inclusion
        if norm_origin in sched_orig and norm_dest in sched_dest:
            dur = item.get("duration_minutes", 60)
            if max_duration_minutes and dur > max_duration_minutes:
                continue

            booked = item.get("booked_seats", 10)
            available = 50 - booked
            confidence = calculate_confidence_score(
                regularity_rate=item.get("regularity_rate", 85.0),
                cancellation_rate=item.get("cancellation_rate", 5.0),
                walking_minutes=walking_minutes,
                available_seats=available,
                requested_pax=requested_pax
            )

            status_jauge = "sufficient" if requested_pax <= available else "insufficient"
            results.append({
                "train_number": item["train_number"],
                "axe": item.get("axe", "Réseau liO Occitanie"),
                "departure_station": item["origin"],
                "arrival_station": item["destination"],
                "departure_time": item["departure_time"],
                "arrival_time": item["arrival_time"],
                "duration_minutes": dur,
                "duration_formatted": f"{dur // 60}h{dur % 60:02d}" if dur >= 60 else f"{dur} min",
                "group_capacity": {
                    "max_limit": 50,
                    "booked_seats": booked,
                    "available_seats": available,
                    "requested_seats": requested_pax,
                    "status": status_jauge,
                    "message": (
                        f"🟢 {available} places disponibles pour {requested_pax} voyageurs"
                        if status_jauge == "sufficient"
                        else f"🔴 Capacité insuffisante : {available} places disponibles pour {requested_pax} demandées"
                    )
                },
                "accessibility_site": {
                    "walking_minutes": walking_minutes,
                    "is_under_20_min": walking_minutes <= 20,
                    "label": f"Gare → site : {walking_minutes} min à pied" + (" (🟢 Recommandé)" if walking_minutes <= 20 else " (⚠️ Vigilance)")
                },
                "confidence_indicator": confidence
            })

    # Trier par heure de départ
    results.sort(key=lambda x: x["departure_time"])
    return results

