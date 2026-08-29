from __future__ import annotations

import json
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.schemas.assistant import AssistantLLMResponse
from app.schemas.planner import ViewingPlannerLLMResponse
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_MS = 45_000
RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504]

ResponseSchema = TypeVar("ResponseSchema", bound=BaseModel)


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
        return self._generate(
            model=self.settings.gemini_viewing_planner_model,
            prompt=prompt,
            response_schema=ViewingPlannerLLMResponse,
        )

    def generate_assistant_reply(
        self,
        *,
        prompt: str,
    ) -> AssistantLLMResponse:
        return self._generate(
            model=self.settings.gemini_assistant_model,
            prompt=prompt,
            response_schema=AssistantLLMResponse,
        )

    def _generate(
        self,
        *,
        model: str,
        prompt: str,
        response_schema: type[ResponseSchema],
    ) -> ResponseSchema:
        if not self.is_configured():
            raise RuntimeError("Gemini LLM service is not configured.")

        genai, types, errors = self._load_sdk()
        client = genai.Client(
            api_key=self.settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(
                    attempts=3,
                    initial_delay=1.0,
                    max_delay=8.0,
                    exp_base=2.0,
                    jitter=0.5,
                    http_status_codes=RETRYABLE_STATUS_CODES,
                ),
            ),
        )

        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
        except errors.APIError as exc:
            status = getattr(exc, "status", None)
            logger.warning("Gemini API error while calling model %s (status=%s): %s", model, status, exc)
            if status == 429:
                raise RuntimeError(f"Gemini rate limit exceeded for model {model}.") from exc
            raise RuntimeError(f"Gemini API error (status={status}) for model {model}.") from exc
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning("Gemini request timed out or could not connect for model %s: %s", model, exc)
            raise RuntimeError(f"Gemini request timed out for model {model}.") from exc

        return self._parse_response(response, response_schema, model=model)

    def _parse_response(
        self,
        response,
        response_schema: type[ResponseSchema],
        *,
        model: str,
    ) -> ResponseSchema:
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, response_schema):
                return parsed
            try:
                return response_schema.model_validate(parsed)
            except ValidationError as exc:
                logger.warning(
                    "Gemini model %s returned a pre-parsed response that failed schema validation: %s",
                    model,
                    exc,
                )
                raise RuntimeError("Gemini returned a response that did not match the expected schema.") from exc

        text = getattr(response, "text", None)
        if not text:
            logger.warning("Gemini model %s returned an empty response.", model)
            raise RuntimeError(f"Gemini returned an empty {response_schema.__name__} response.")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("Gemini model %s returned malformed JSON: %s", model, exc)
            raise RuntimeError("Gemini returned a response that was not valid JSON.") from exc

        try:
            return response_schema.model_validate(data)
        except ValidationError as exc:
            logger.warning("Gemini model %s returned JSON that failed schema validation: %s", model, exc)
            raise RuntimeError("Gemini returned a response that did not match the expected schema.") from exc

    def _load_sdk(self):
        try:
            from google import genai
            from google.genai import errors, types
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise RuntimeError(
                "google-genai is not installed. Install it to use the Gemini viewing planner."
            ) from exc
        return genai, types, errors
