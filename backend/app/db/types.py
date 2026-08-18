from __future__ import annotations

from sqlalchemy import JSON, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.types import TypeDecorator, UserDefinedType

PGVECTOR_SUPPORT_ATTR = "_smart_semantic_web_tv_pgvector_supported"
PGVECTOR_CHECKED_ATTR = "_smart_semantic_web_tv_pgvector_checked"


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
        if pgvector_supported(dialect):
            return dialect.type_descriptor(_PGVectorType(self.dimensions))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        normalized = [float(item) for item in value]
        if pgvector_supported(dialect):
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


def pgvector_supported(dialect) -> bool:
    return bool(getattr(dialect, PGVECTOR_SUPPORT_ATTR, False))


def configure_pgvector_support(bind: Engine | Connection | None) -> bool:
    if bind is None:
        return False

    dialect = bind.dialect
    if getattr(dialect, PGVECTOR_CHECKED_ATTR, False):
        return pgvector_supported(dialect)

    supported = False
    if dialect.name == "postgresql":
        try:
            if isinstance(bind, Engine):
                with bind.connect() as connection:
                    supported = bool(
                        connection.execute(
                            text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector')")
                        ).scalar()
                    )
            else:
                supported = bool(
                    bind.execute(
                        text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector')")
                    ).scalar()
                )
        except Exception:
            supported = False

    setattr(dialect, PGVECTOR_SUPPORT_ATTR, supported)
    setattr(dialect, PGVECTOR_CHECKED_ATTR, True)
    return supported
