"""Module LLM local et extraction de voyages scolaires liO."""
from .schemas import TravelInfo, ExtractionRequest
from .extractor import TravelExtractor, postprocess
from .client import LLMClient, LLMError
from .pedagogical import analyze_request

__all__ = [
    "TravelInfo",
    "ExtractionRequest",
    "TravelExtractor",
    "postprocess",
    "LLMClient",
    "LLMError",
    "analyze_request",
]

