from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db import base  # noqa: F401


def _configure_sqlite_connection(dbapi_connection, connection_record) -> None:
    # WAL lets the API server keep reading while a sync command (live TV / EPG / catalog /
    # search index) writes, instead of the two blocking each other on the default rollback
    # journal. busy_timeout replaces an indefinite lock wait with a bounded one.
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()


def create_db_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    url = database_url or settings.database_url
    engine_kwargs: dict[str, object] = {"pool_pre_ping": True}

    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(url, **engine_kwargs)

    if url.startswith("sqlite") and ":memory:" not in url:
        event.listen(engine, "connect", _configure_sqlite_connection)

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def session_scope() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
