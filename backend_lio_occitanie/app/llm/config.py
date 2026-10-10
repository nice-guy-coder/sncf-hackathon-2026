"""Configuration centralisée du client LLM."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # URL du serveur llama.cpp (API compatible OpenAI)
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://llm:8080")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "120"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "256"))
    # Fuseau utilisé pour résoudre les dates relatives ("demain", "vendredi"...)
    timezone: str = os.getenv("TZ", "Europe/Paris")


settings = Settings()

