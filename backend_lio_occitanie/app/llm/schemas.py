"""Schémas d'entrée / sortie de l'API et schéma JSON imposé au LLM."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=4000,
                             examples=["Nous partons à 3 de Lyon pour Marseille le 12 juillet, retour le 20."])


class TravelInfo(BaseModel):
    """Sortie finale renvoyée à l'utilisateur."""
    nombre_personnes: Optional[int] = Field(None, description="Nombre total de voyageurs (null si non précisé)")
    date_depart: Optional[str] = Field(None, description="Date de départ au format YYYY-MM-DD (null si non précisé)")
    date_arrivee: Optional[str] = Field(None, description="Date d'arrivée / de retour au format YYYY-MM-DD (null si non précisé)")
    lieu_depart: Optional[str] = Field(None, description="Ville ou gare de départ (null si non précisé)")
    destination: Optional[str] = Field(None, description="Destination précise (null si non précisé)")
    destination_connue: bool = Field(False, description="True si une destination précise est mentionnée")


def _nullable(type_: str) -> dict:
    return {"anyOf": [{"type": type_}, {"type": "null"}]}


# Schéma transmis à llama.cpp : il est converti en grammaire GBNF, ce qui
# GARANTIT que le modèle produit un JSON valide respectant cette structure.
# Les dates sont demandées "telles qu'écrites" : la normalisation est faite en
# Python (les petits modèles calculent mal les dates relatives).
LLM_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "nombre_personnes": _nullable("integer"),
        "date_depart": _nullable("string"),
        "date_arrivee": _nullable("string"),
        "lieu_depart": _nullable("string"),
        "destination": _nullable("string"),
    },
    "required": ["nombre_personnes", "date_depart", "date_arrivee", "lieu_depart", "destination"],
    "additionalProperties": False,
}
