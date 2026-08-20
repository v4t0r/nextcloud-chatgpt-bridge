from __future__ import annotations

import argparse
from importlib.resources import files

_INITIAL_MIGRATION = "0001_hosted_storage.sql"


def initial_migration_sql() -> str:
    """Return the packaged initial PostgreSQL migration."""
    return (
        files("nextcloud_chatgpt_bridge.migrations")
        .joinpath(_INITIAL_MIGRATION)
        .read_text(encoding="utf-8")
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print the packaged PostgreSQL schema migration for hosted deployments."
    )
    parser.parse_args()
    print(initial_migration_sql(), end="")


if __name__ == "__main__":
    main()
