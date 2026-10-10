"""Orchestration : LLM -> validation anti-hallucination -> normalisation -> JSON final."""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Optional, Protocol
from zoneinfo import ZoneInfo

from .config import settings
from .date_utils import has_date_cue, normalize_date, split_range, strip_accents
from .schemas import TravelInfo

logger = logging.getLogger(__name__)

STOPWORDS = {"de", "du", "des", "la", "le", "les", "l", "d", "a", "au", "aux", "en", "pour", "vers", "gare", "depuis"}
VAGUE_DESTINATIONS = {"inconnu", "inconnue", "quelque part", "n'importe ou", "nimporte ou", "partout",
                      "ailleurs", "non precise", "null", "none", "?", ""}


class RawExtractor(Protocol):
    def extract_raw(self, description: str) -> dict[str, Any]: ...


def _norm(text: str) -> str:
    text = strip_accents(text.lower()).replace("’", "'")
    return re.sub(r"[^a-z0-9']+", " ", text).strip()


def _clean_place(value: Any, description: str) -> Optional[str]:
    """Garde un lieu uniquement s'il apparaît réellement dans la description."""
    if not isinstance(value, str):
        return None
    value = value.strip(" .,;:!?\"'")
    value = re.sub(r"^(?:de|du|d'|depuis|à|a|au|aux|pour|vers|en)\s+", "", value, flags=re.I).strip()
    if _norm(value) in VAGUE_DESTINATIONS:
        return None
    text = f" {_norm(description)} "
    norm_value = _norm(value)
    if f" {norm_value} " in text:
        return value
    tokens = [t for t in norm_value.replace("'", " ").split() if t not in STOPWORDS and len(t) > 1]
    if tokens and all(f" {t}" in text for t in tokens):
        return value
    return None  # valeur absente du texte -> hallucination probable


def _clean_count(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and 0 < int(value) < 1000:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return _clean_count(int(value.strip()))
    return None


def _clean_date_expr(value: Any, description: str) -> Optional[str]:
    if not isinstance(value, str) or not value.strip() or _norm(value) in {"null", "none"}:
        return None
    if not has_date_cue(description) or not has_date_cue(value):
        return None
    return value.strip()


_TO_PREP = r"(?:à|a|au|aux|pour|vers|direction|destination de|destination|jusqu'à|jusqu'a|en)"
_FROM_PREP = r"(?:de|d'|du|des|depuis|départ de|au départ de)"


def _preceded_by(place: str, prep: str, description: str) -> bool:
    return bool(re.search(rf"\b{prep}\s*{re.escape(place)}", description, re.I))


def _fix_roles(lieu_depart: Optional[str], destination: Optional[str],
               description: str) -> tuple[Optional[str], Optional[str]]:
    """Corrige les inversions départ/destination à partir des prépositions du texte."""
    if destination and lieu_depart and _norm(destination) == _norm(lieu_depart):
        if _preceded_by(destination, _TO_PREP, description):
            return None, destination
        return lieu_depart, None
    if lieu_depart and not destination and _preceded_by(lieu_depart, _TO_PREP, description) \
            and not _preceded_by(lieu_depart, _FROM_PREP, description):
        return None, lieu_depart
    if destination and not lieu_depart and _preceded_by(destination, _FROM_PREP, description) \
            and not _preceded_by(destination, _TO_PREP, description):
        return destination, None
    return lieu_depart, destination


def today() -> date:
    return datetime.now(ZoneInfo(settings.timezone)).date()


def postprocess(raw: dict[str, Any], description: str, ref: Optional[date] = None) -> TravelInfo:
    ref = ref or today()

    depart_expr = _clean_date_expr(raw.get("date_depart"), description)
    retour_expr = _clean_date_expr(raw.get("date_retour"), description)

    if (rng := split_range(depart_expr)):
        depart_expr = rng[0]
        retour_expr = retour_expr if retour_expr and not split_range(retour_expr) else rng[1]
    elif (rng := split_range(retour_expr)):
        retour_expr = rng[1]
        depart_expr = depart_expr or rng[0]

    date_depart = normalize_date(depart_expr, ref)

    retour_ref = ref
    if date_depart and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_depart):
        try:
            retour_ref = date.fromisoformat(date_depart)
        except ValueError:
            pass

    date_retour = normalize_date(retour_expr, retour_ref)
    if date_retour == date_depart and retour_expr == depart_expr:
        date_retour = None

    destination = _clean_place(raw.get("destination"), description)
    lieu_depart = _clean_place(raw.get("lieu_depart"), description)
    lieu_depart, destination = _fix_roles(lieu_depart, destination, description)

    return TravelInfo(
        nombre_personnes=_clean_count(raw.get("nombre_personnes")),
        date_depart=date_depart,
        date_retour=date_retour,
        lieu_depart=lieu_depart,
        destination=destination,
        destination_connue=destination is not None,
    )


def extract_heuristic_fallback(description: str, ref: Optional[date] = None) -> TravelInfo:
    """Fallback d'extraction en cas d'indisponibilité du serveur llama.cpp."""
    ref = ref or today()
    low = description.lower()

    # Détection nombre de personnes
    pax = None
    m_pax = re.search(r"\b(\d{1,3})\s+(?:élèves|eleves|personnes|voyageurs|enfants|passagers|places|adultes)\b", low)
    if m_pax:
        pax = int(m_pax.group(1))
    elif re.search(r"\b(?:seul|seule|moi seul)\b", low):
        pax = 1

    # Détection départ
    dep = None
    m_dep = re.search(r"(?:au départ de|depart de|depuis|partons du collège de|partons de|de)\s+([A-Za-zÀ-ÿ' -]{2,40})", description, re.I)
    if m_dep:
        val = re.split(r",|\.|\s+le\s+|\s+pour\s+|\s+avec\s+|\s+vers\s+", m_dep.group(1), flags=re.I)[0].strip()
        val = re.sub(r"^(?:collège de|college de|gare de|gare d')\s*", "", val, flags=re.I).strip()
        dep = val.capitalize() if val else None

    # Détection destination
    dest = None
    m_dest = re.search(r"(?:à destination de|destination|visiter|(?:pour\s+)?aller à|(?:pour\s+)?aller a|vers|pour)\s+([A-Za-zÀ-ÿ' -]{2,40})", description, re.I)
    if m_dest:
        val = re.split(r",|\.|\s+le\s+|\s+avec\s+|\s+au départ\s+", m_dest.group(1), flags=re.I)[0].strip()
        val = re.sub(r"^(?:la ville de|la gare de)\s*", "", val, flags=re.I).strip()
        if val and (not dep or val.lower() != dep.lower()):
            dest = val.capitalize()

    # Détection date
    date_dep = None
    m_date = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", description)
    if m_date:
        date_dep = m_date.group(1)
    else:
        m_cue = re.search(r"\b(?:le\s+\d{1,2}(?:er)?\s+[a-z]+|\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?|demain|vendredi|lundi)\b", low)
        if m_cue:
            date_dep = normalize_date(m_cue.group(0), ref)

    return TravelInfo(
        nombre_personnes=pax,
        date_depart=date_dep,
        date_retour=None,
        lieu_depart=dep,
        destination=dest,
        destination_connue=dest is not None,
    )


class TravelExtractor:
    def __init__(self, llm: RawExtractor):
        self.llm = llm

    def extract(self, description: str, ref: Optional[date] = None) -> TravelInfo:
        try:
            raw = self.llm.extract_raw(description)
            return postprocess(raw, description, ref)
        except Exception as exc:
            logger.warning(f"Serveur LLM inaccessible ({exc}), bascule sur l'extracteur heuristique.")
            return extract_heuristic_fallback(description, ref)

