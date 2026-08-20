from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from nextcloud_chatgpt_bridge.persistence import PersistenceError

EXPECTED_SCHEMA_VERSION = 2


def verify_hosted_schema(engine: Engine) -> None:
    """Refuse hosted startup unless the database has the exact expected schema version."""
    try:
        with engine.connect() as connection:
            version = connection.scalar(
                text("SELECT MAX(version) FROM bridge_schema_migrations")
            )
    except SQLAlchemyError as exc:
        raise PersistenceError("Hosted database schema is unavailable or not initialized") from exc

    if version != EXPECTED_SCHEMA_VERSION:
        raise PersistenceError(
            f"Hosted database schema version mismatch: expected {EXPECTED_SCHEMA_VERSION}"
        )
