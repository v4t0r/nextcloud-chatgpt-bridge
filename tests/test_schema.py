from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from nextcloud_chatgpt_bridge.migration import (
    all_migrations_sql,
    initial_migration_sql,
    migration_sql,
)
from nextcloud_chatgpt_bridge.persistence import PersistenceError
from nextcloud_chatgpt_bridge.schema import verify_hosted_schema


def test_initial_migration_is_packaged_and_versioned():
    migration = initial_migration_sql()

    assert "CREATE TABLE bridge_schema_migrations" in migration
    assert "INSERT INTO bridge_schema_migrations (version) VALUES (1)" in migration
    assert "CREATE TABLE household_profiles" in migration_sql(2)
    assert "INSERT INTO bridge_schema_migrations (version) VALUES (2)" in all_migrations_sql()


def test_schema_verifier_accepts_exact_expected_version():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE bridge_schema_migrations (version INTEGER PRIMARY KEY)")
        )
        connection.execute(text("INSERT INTO bridge_schema_migrations (version) VALUES (2)"))

    verify_hosted_schema(engine)


def test_schema_verifier_rejects_missing_schema():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with pytest.raises(PersistenceError, match="unavailable|initialized"):
        verify_hosted_schema(engine)


def test_schema_verifier_rejects_wrong_version():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE bridge_schema_migrations (version INTEGER PRIMARY KEY)")
        )
        connection.execute(text("INSERT INTO bridge_schema_migrations (version) VALUES (3)"))

    with pytest.raises(PersistenceError, match="version mismatch"):
        verify_hosted_schema(engine)
