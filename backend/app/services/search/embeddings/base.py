from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def embed_document(self, *, title: str | None, text: str) -> list[float]:
        raise NotImplementedError
