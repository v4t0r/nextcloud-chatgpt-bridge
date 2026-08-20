from __future__ import annotations

import argparse
from importlib.resources import files

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
    args = parser.parse_args()
    if args.list:
        print("\n".join(str(version) for version in sorted(_MIGRATIONS)))
        return
    print(migration_sql(args.version) if args.version else all_migrations_sql(), end="")


if __name__ == "__main__":
    main()
