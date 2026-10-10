"""Normalisation déterministe des expressions de date françaises en ISO 8601.

Le LLM recopie l'expression telle qu'elle apparaît ("demain", "le 12 juillet",
"vendredi prochain", "12/07"...). Ce module la convertit en "YYYY-MM-DD" à
partir d'une date de référence. Si l'expression n'est pas interprétable, la
fonction renvoie le texte brut (on ne perd pas l'information).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from typing import Optional

WEEKDAYS = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
            "vendredi": 4, "samedi": 5, "dimanche": 6}

# Préfixes (sans accents) -> numéro de mois. L'ordre compte : "juil" avant "juin".
MONTH_PREFIXES = [("janv", 1), ("jan", 1), ("fev", 2), ("mars", 3), ("mar", 3),
                  ("avr", 4), ("mai", 5), ("juin", 6), ("juil", 7), ("aou", 8),
                  ("sep", 9), ("oct", 10), ("nov", 11), ("dec", 12)]

ISO_RE = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})\s*$")
NUMERIC_RE = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b")
DAY_MONTH_RE = re.compile(r"\b(\d{1,2})(?:er)?\s+([a-z]+)\.?(?:\s+(\d{4}))?\b")
DAY_ONLY_RE = re.compile(r"\b(?:le\s+)?(\d{1,2})(?:er)?\b")
IN_N_RE = re.compile(r"\bdans\s+(\d+|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)\s+(jours?|semaines?|mois)\b")
WORD_NUMBERS = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
                "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10}

# Indices permettant de vérifier qu'une date est réellement évoquée dans le texte
_MONTH_WORDS = (r"janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre"
                r"|janv|fev|avr|juil|sept|oct|nov|dec")
DATE_CUES = re.compile(
    r"\b(?:" + _MONTH_WORDS + "|" + "|".join(WEEKDAYS) + r")\b"
    r"|demain|aujourd|ce soir|ce matin|semaine|week.?end|\bmois\b|\bdans \w+ jours?"
    r"|\b\d{1,2}[/.\-]\d{1,2}\b|\b\d{4}-\d{2}-\d{2}\b|\b(?:le|du|au|jusqu'au)\s+\d{1,2}(?:er)?\b"
)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(text.lower()).replace("’", "'")).strip()


def _month_from_word(word: str) -> Optional[int]:
    for prefix, month in MONTH_PREFIXES:
        if word.startswith(prefix):
            return month
    return None


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def normalize_date(expr: Optional[str], ref: date) -> Optional[str]:
    """Transforme une expression libre en "YYYY-MM-DD". Renvoie l'expression brute si non résolue."""
    if not expr:
        return None
    raw = expr.strip()
    if ISO_RE.match(raw):
        return raw

    s = _norm(raw)

    if s in {"aujourd'hui", "aujourdhui", "ce jour", "ce soir", "ce matin"}:
        return ref.isoformat()
    if s == "demain":
        return (ref + timedelta(days=1)).isoformat()
    if s in {"apres-demain", "apres demain"}:
        return (ref + timedelta(days=2)).isoformat()

    # "dans N jours / semaines / mois"
    if (m := IN_N_RE.search(s)):
        n_str, unit = m.group(1), m.group(2)
        n = int(n_str) if n_str.isdigit() else WORD_NUMBERS.get(n_str, 0)
        if unit.startswith("jour"):
            return (ref + timedelta(days=n)).isoformat()
        if unit.startswith("semaine"):
            return (ref + timedelta(days=7 * n)).isoformat()
        if unit.startswith("mois"):
            month = ref.month + n
            year = ref.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            d = _safe_date(year, month, min(ref.day, 28))
            return d.isoformat() if d else None

    # "vendredi prochain", "vendredi en huit", ou juste "vendredi"
    for day_name, target_weekday in WEEKDAYS.items():
        if re.search(rf"\b{day_name}\b", s):
            days_ahead = (target_weekday - ref.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            if "en huit" in s:
                days_ahead += 7
            return (ref + timedelta(days=days_ahead)).isoformat()

    # "12 juillet", "1er mai", "15 aout 2026"
    if (m := DAY_MONTH_RE.search(s)):
        day = int(m.group(1))
        month = _month_from_word(m.group(2))
        if month:
            year = int(m.group(3)) if m.group(3) else ref.year
            d = _safe_date(year, month, day)
            if not m.group(3) and d and d < ref:
                d = _safe_date(year + 1, month, day)
            if d:
                return d.isoformat()

    # "12/07", "12/07/2026", "12-07"
    if (m := NUMERIC_RE.search(s)):
        day, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            raw_y = m.group(3)
            if raw_y:
                year = int(raw_y) if len(raw_y) == 4 else 2000 + int(raw_y)
            else:
                year = ref.year
            d = _safe_date(year, month, day)
            if not raw_y and d and d < ref:
                d = _safe_date(year + 1, month, day)
            if d:
                return d.isoformat()

    # "le 20" (sans mois précisé -> mois courant, ou suivant si déjà passé)
    if (m := DAY_ONLY_RE.fullmatch(s)):
        day = int(m.group(1))
        d = _safe_date(ref.year, ref.month, day)
        if d and d < ref:
            m_next = (ref.month % 12) + 1
            y_next = ref.year + (1 if m_next == 1 else 0)
            d = _safe_date(y_next, m_next, day)
        if d:
            return d.isoformat()

    return raw


def has_date_cue(text: str) -> bool:
    """Vérifie si le texte évoque au moins un élément temporel crédible."""
    return bool(DATE_CUES.search(_norm(text)))


def split_range(text: Optional[str]) -> Optional[tuple[str, str]]:
    """Détecte 'du X au Y' et renvoie ('X', 'Y')."""
    if not text:
        return None
    s = _norm(text)
    m = re.search(r"^(?:du|de)\s+(.+?)\s+(?:au|a|jusqu'au)\s+(.+)$", s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None

