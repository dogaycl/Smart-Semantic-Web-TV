from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.assistant import AssistantLLMResponse
from app.schemas.planner import ViewingPlannerLLMResponse


class LLMService(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_viewing_plan(
        self,
        *,
        prompt: str,
    ) -> ViewingPlannerLLMResponse:
        raise NotImplementedError

    @abstractmethod
    def generate_assistant_reply(
        self,
        *,
        prompt: str,
    ) -> AssistantLLMResponse:
        raise NotImplementedError
