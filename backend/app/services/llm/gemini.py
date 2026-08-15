from __future__ import annotations

import json

from app.core.config import get_settings
from app.schemas.planner import ViewingPlannerLLMResponse
from app.services.llm.base import LLMService


class GeminiLLMService(LLMService):
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def generate_viewing_plan(
        self,
        *,
        prompt: str,
    ) -> ViewingPlannerLLMResponse:
        if not self.is_configured():
            raise RuntimeError("Gemini LLM service is not configured.")

        genai, types = self._load_sdk()
        client = genai.Client(api_key=self.settings.gemini_api_key)
        response = client.models.generate_content(
            model=self.settings.gemini_viewing_planner_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ViewingPlannerLLMResponse,
            ),
        )

        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, ViewingPlannerLLMResponse):
                return parsed
            return ViewingPlannerLLMResponse.model_validate(parsed)

        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty planner response.")
        return ViewingPlannerLLMResponse.model_validate(json.loads(text))

    def _load_sdk(self):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise RuntimeError(
                "google-genai is not installed. Install it to use the Gemini viewing planner."
            ) from exc
        return genai, types
