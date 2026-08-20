#!/bin/sh
set -eu

database_password_file="${BRIDGE_DB_PASSWORD_FILE:-/run/secrets/bridge_db_password}"
keyring_file="${BRIDGE_KEYRING_FILE:-/run/secrets/bridge_secret_keyring}"

test -r "$database_password_file"
test -r "$keyring_file"

database_password_encoded="$(python -c 'import sys; from urllib.parse import quote; print(quote(sys.stdin.read().strip(), safe=""))' < "$database_password_file")"
export BRIDGE_DATABASE_URL="postgresql+psycopg://bridge:${database_password_encoded}@database:5432/bridge"
export BRIDGE_SECRET_KEYS_JSON="$(cat "$keyring_file")"

exec "$@"
