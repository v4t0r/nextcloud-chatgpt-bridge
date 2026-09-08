#!/bin/bash
set -euo pipefail
export KC_DB_PASSWORD="$(cat /run/secrets/auth_db_password)"
export KC_BOOTSTRAP_ADMIN_PASSWORD="$(cat /run/secrets/auth_admin_password)"
export BRIDGE_OAUTH_CLIENT_SECRET="$(cat /run/secrets/auth_client_secret)"
exec /opt/keycloak/bin/kc.sh "$@"
