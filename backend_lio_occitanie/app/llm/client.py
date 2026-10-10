"""Client HTTP vers le serveur llama.cpp (endpoint OpenAI-compatible)."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .config import settings
from .schemas import LLM_JSON_SCHEMA

SYSTEM_PROMPT = """Tu es un extracteur d'informations de voyage. On te donne une description en français.
Tu réponds UNIQUEMENT avec un objet JSON contenant ces clés :
- "nombre_personnes" : nombre TOTAL de voyageurs (entier). "je" seul = 1 ; "ma femme et moi" = 2 ; "nous" sans précision = null.
- "date_depart" : expression de la date de départ, recopiée telle qu'écrite dans le texte (ex. "le 12 juillet", "demain", "vendredi prochain").
- "date_retour" : expression de la date de retour, recopiée telle qu'écrite.
- "lieu_depart" : ville ou gare de départ.
- "destination" : ville, pays ou lieu de destination précis.
Règles strictes :
- Si une information n'est PAS dans le texte, mets null. N'invente JAMAIS rien.
- Une destination vague ("quelque part", "n'importe où", "je ne sais pas encore où") = null.
- Recopie les noms de lieux comme dans le texte, sans préposition ("de", "à", "pour")."""

FEW_SHOTS: list[tuple[str, dict[str, Any]]] = [
    (
        "Bonjour, nous sommes 4 et souhaitons aller de Lyon à Marseille le 15 août, retour le 22 août.",
        {"nombre_personnes": 4, "date_depart": "le 15 août", "date_retour": "le 22 août",
         "lieu_depart": "Lyon", "destination": "Marseille"},
    ),
    (
        "Je voudrais partir de Bordeaux demain, mais je ne sais pas encore où aller.",
        {"nombre_personnes": 1, "date_depart": "demain", "date_retour": None,
         "lieu_depart": "Bordeaux", "destination": None},
    ),
    (
        "Avec ma femme et nos deux enfants on veut aller à Nice.",
        {"nombre_personnes": 4, "date_depart": None, "date_retour": None,
         "lieu_depart": None, "destination": "Nice"},
    ),
    (
        "Je voudrais un billet pour Strasbourg avec mon frère vendredi.",
        {"nombre_personnes": 2, "date_depart": "vendredi", "date_retour": None,
         "lieu_depart": None, "destination": "Strasbourg"},
    ),
]


def build_messages(description: str) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for text, answer in FEW_SHOTS:
        messages.append({"role": "user", "content": text})
        messages.append({"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)})
    messages.append({"role": "user", "content": description})
    return messages


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self._timeout = timeout or settings.llm_timeout_s

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                return client.get(f"{self.base_url}/health").status_code == 200
        except (httpx.HTTPError, Exception):
            return False

    def extract_raw(self, description: str) -> dict[str, Any]:
        payload = {
            "messages": build_messages(description),
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "cache_prompt": True,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "travel_info", "schema": LLM_JSON_SCHEMA, "strict": True},
            },
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return json.loads(content)
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMError(f"Échec de l'appel au LLM ({self.base_url}) : {exc}") from exc

