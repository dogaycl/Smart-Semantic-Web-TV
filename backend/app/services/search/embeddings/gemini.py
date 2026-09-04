from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.services.search.embeddings.base import EmbeddingService

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
BASE_RETRY_DELAY_SECONDS = 2.0
MAX_RETRY_DELAY_SECONDS = 8.0

# Circuit breaker: once the free embedding quota is exhausted (HTTP 429), every later call would
# burn ~6s of back-off before failing the same way. Remember the exhaustion and fail fast for a
# cooldown so search / assistant / planner stay responsive on their lexical fallback.
_QUOTA_COOLDOWN = timedelta(minutes=15)
_quota_lock = threading.Lock()
_quota_exhausted_until: datetime | None = None


def _quota_is_exhausted() -> bool:
    with _quota_lock:
        return _quota_exhausted_until is not None and datetime.now(timezone.utc) < _quota_exhausted_until


def _mark_quota_exhausted() -> None:
    global _quota_exhausted_until
    with _quota_lock:
        _quota_exhausted_until = datetime.now(timezone.utc) + _QUOTA_COOLDOWN


class QuotaExhaustedError(RuntimeError):
    """Raised (fast) while the embedding quota is known to be exhausted."""


class GeminiEmbeddingService(EmbeddingService):
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def embed_query(self, query: str) -> list[float]:
        return self._embed_text(f"task: search result | query: {query}")

    def embed_document(self, *, title: str | None, text: str) -> list[float]:
        normalized_title = title or "none"
        return self._embed_text(f"title: {normalized_title} | text: {text}")

    def _embed_text(self, text: str) -> list[float]:
        if not self.is_configured():
            raise RuntimeError("Gemini embedding service is not configured.")
        if _quota_is_exhausted():
            raise QuotaExhaustedError("Gemini embedding quota is exhausted; skipping the call.")

        model = self.settings.gemini_embedding_model.replace("models/", "")

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.settings.gemini_api_key or "",
                    },
                    json={
                        "model": f"models/{model}",
                        "content": {
                            "parts": [
                                {
                                    "text": text,
                                }
                            ]
                        },
                        # outputDimensionality is a top-level field on the v1beta embedContent
                        # request. Nested under a config key it is silently ignored and the model
                        # returns its native dimension (3072 for gemini-embedding-001), which then
                        # mismatches GEMINI_EMBEDDING_DIMENSIONS and the stored vectors.
                        "outputDimensionality": self.settings.gemini_embedding_dimensions,
                    },
                    timeout=self.settings.search_request_timeout_seconds,
                )
            except httpx.HTTPError as exc:
                if attempt == MAX_ATTEMPTS:
                    raise
                logger.warning(
                    "Gemini embedding request failed (attempt %s/%s), retrying: %s",
                    attempt, MAX_ATTEMPTS, exc,
                )
                time.sleep(self._retry_delay(attempt=attempt, response=None))
                continue

            if response.status_code == 429:
                _mark_quota_exhausted()
                logger.warning("Gemini embedding quota exhausted (HTTP 429); pausing embedding calls.")
                raise QuotaExhaustedError("Gemini embedding quota is exhausted.")

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_ATTEMPTS:
                logger.warning(
                    "Gemini embedding request got HTTP %s (attempt %s/%s), retrying.",
                    response.status_code, attempt, MAX_ATTEMPTS,
                )
                time.sleep(self._retry_delay(attempt=attempt, response=response))
                continue

            response.raise_for_status()
            payload = response.json()
            embedding = payload.get("embedding") or {}
            values = embedding.get("values") or []
            return [float(item) for item in values]

        raise RuntimeError("Gemini embedding request failed after retries.")

    def _retry_delay(self, *, attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            header_value = response.headers.get("retry-after")
            if header_value:
                try:
                    return min(float(header_value), MAX_RETRY_DELAY_SECONDS)
                except ValueError:
                    pass
        return min(BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)), MAX_RETRY_DELAY_SECONDS)
