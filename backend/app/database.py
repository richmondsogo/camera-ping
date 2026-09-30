from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy import Dialect, Engine, MetaData, create_engine, event, types
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Constraint naming convention for stable SQLite batch migrations
naming_convention: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)


class Base(DeclarativeBase):
    metadata = metadata


class UTCDateTime(types.TypeDecorator[datetime]):
    """Timezone-aware UTC datetime type.

    Rejects naive datetimes on write and always returns timezone-aware UTC
    datetimes on read.
    """

    impl = types.DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                msg = (
                    "UTCDateTime requires timezone-aware datetime, "
                    f"got naive: {value!r}"
                )
                raise ValueError(msg)
            return value.astimezone(UTC)
        return None

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        return None


def configure_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    """Configure SQLite PRAGMAs: WAL mode, foreign keys, and 5000ms busy timeout."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def create_db_engine(database_url: str) -> Engine:
    """Create a database engine with SQLite pragmas attached if applicable."""
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    engine = create_engine(database_url, connect_args=connect_args)
    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", configure_sqlite_pragmas)
    return engine


def create_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    """Create a SessionLocal factory bound to the given engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db(request: Request) -> Generator[Session, None, None]:
    """FastAPI dependency providing a database session from app.state."""
    session_factory: sessionmaker[Session] = request.app.state.sessionmaker
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
