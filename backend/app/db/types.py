from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator, UserDefinedType


class _PGVectorType(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int | None = None) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **kwargs) -> str:
        if self.dimensions is None:
            return "vector"
        return f"vector({self.dimensions})"


class EmbeddingVector(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int | None = None) -> None:
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PGVectorType(self.dimensions))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        normalized = [float(item) for item in value]
        if dialect.name == "postgresql":
            return vector_literal(normalized)
        return normalized

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                inner = stripped[1:-1].strip()
                if not inner:
                    return []
                return [float(part) for part in inner.split(",")]

        return [float(item) for item in value]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(item):.8f}".rstrip("0").rstrip(".") for item in values) + "]"
