from __future__ import annotations

import argparse
import json
from importlib.resources import files

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from nextcloud_chatgpt_bridge.persistence import HostedStorageConfig, create_hosted_engine
from nextcloud_chatgpt_bridge.schema import EXPECTED_SCHEMA_VERSION, verify_hosted_schema

_MIGRATIONS = {
    1: "0001_hosted_storage.sql",
    2: "0002_household_profiles.sql",
}


def initial_migration_sql() -> str:
    """Return the packaged initial PostgreSQL migration."""
    return (
        files("nextcloud_chatgpt_bridge.migrations")
        .joinpath(_MIGRATIONS[1])
        .read_text(encoding="utf-8")
    )


def migration_sql(version: int) -> str:
    """Return one packaged PostgreSQL migration by schema version."""
    name = _MIGRATIONS.get(version)
    if name is None:
        raise ValueError(f"Unknown schema migration version: {version}")
    return files("nextcloud_chatgpt_bridge.migrations").joinpath(name).read_text(encoding="utf-8")


def all_migrations_sql() -> str:
    """Return every packaged migration in application order."""
    return "\n".join(migration_sql(version).rstrip() for version in sorted(_MIGRATIONS)) + "\n"


def current_schema_version(engine: Engine) -> int:
    if not inspect(engine).has_table("bridge_schema_migrations"):
        return 0
    with engine.connect() as connection:
        version = connection.scalar(text("SELECT MAX(version) FROM bridge_schema_migrations"))
    return int(version or 0)


def pending_migration_versions(current_version: int) -> tuple[int, ...]:
    if current_version < 0 or current_version > EXPECTED_SCHEMA_VERSION:
        raise ValueError("Hosted database schema version is unsupported")
    return tuple(version for version in sorted(_MIGRATIONS) if version > current_version)


def apply_pending_migrations(engine: Engine) -> tuple[int, ...]:
    """Apply packaged PostgreSQL migrations in order from an explicit operator action."""
    if engine.dialect.name != "postgresql":
        raise ValueError("Hosted migrations can only be applied to PostgreSQL")
    pending = pending_migration_versions(current_schema_version(engine))
    if not pending:
        verify_hosted_schema(engine)
        return ()

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for version in pending:
            connection.exec_driver_sql(migration_sql(version))
    verify_hosted_schema(engine)
    return pending


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print the packaged PostgreSQL schema migration for hosted deployments."
    )
    parser.add_argument(
        "--version",
        type=int,
        choices=tuple(sorted(_MIGRATIONS)),
        help="Print one migration version. The default prints all migrations in order.",
    )
    parser.add_argument("--list", action="store_true", help="List packaged migration versions.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply every pending migration to BRIDGE_DATABASE_URL.",
    )
    args = parser.parse_args()
    if args.apply:
        if args.list or args.version is not None:
            parser.error("--apply cannot be combined with --list or --version")
        engine = create_hosted_engine(HostedStorageConfig())
        try:
            applied = apply_pending_migrations(engine)
        finally:
            engine.dispose()
        print(
            json.dumps(
                {
                    "applied_versions": list(applied),
                    "current_version": EXPECTED_SCHEMA_VERSION,
                },
                sort_keys=True,
            )
        )
        return
    if args.list:
        print("\n".join(str(version) for version in sorted(_MIGRATIONS)))
        return
    print(migration_sql(args.version) if args.version else all_migrations_sql(), end="")


if __name__ == "__main__":
    main()
