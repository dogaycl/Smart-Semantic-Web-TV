from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.search.embeddings.base import EmbeddingService


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

        model = self.settings.gemini_embedding_model.replace("models/", "")
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
                "embedContentConfig": {
                    "outputDimensionality": self.settings.gemini_embedding_dimensions,
                    "autoTruncate": True,
                },
            },
            timeout=self.settings.search_request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        embedding = payload.get("embedding") or {}
        values = embedding.get("values") or []
        return [float(item) for item in values]
