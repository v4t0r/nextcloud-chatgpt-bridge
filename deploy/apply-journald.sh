#!/usr/bin/env bash
# Apply the validated logging change after host journald retention is active.
set -Eeuo pipefail
cd "$HOME/nextcloud-chatgpt-bridge/deploy"
[[ -f compose.npm.yml.new ]] || { echo 'Staged Compose file missing' >&2; exit 1; }
[[ -f /etc/systemd/journald.conf.d/nextcloud-bridge-retention.conf ]] || {
  echo 'Host journal retention is not configured' >&2
  exit 1
}

backup="compose.npm.yml.before-journald.$(date -u +%Y%m%dT%H%M%SZ)"
cp -p compose.npm.yml "$backup"
mv compose.npm.yml.new compose.npm.yml
rollback() {
  local status=$?
  if (( status != 0 )); then
    cp -p "$backup" compose.npm.yml
    docker compose --env-file "$HOME/nextcloud-runtime/production.env" \
      -f compose.production.yml -f compose.npm.yml up -d --no-build || true
    echo "LOG_CHANGE_ROLLED_BACK exit=$status" >&2
  fi
}
trap rollback EXIT

docker compose --env-file "$HOME/nextcloud-runtime/production.env" \
  -f compose.production.yml -f compose.npm.yml config --quiet
docker compose --env-file "$HOME/nextcloud-runtime/production.env" \
  -f compose.production.yml -f compose.npm.yml up -d --no-build

for service in bridge caddy database auth_database keycloak egress maintenance; do
  container="nextcloud-chatgpt-bridge-${service}-1"
  driver="$(docker inspect "$container" --format '{{.HostConfig.LogConfig.Type}}')"
  [[ "$driver" == journald ]] || { echo "Wrong log driver for $service" >&2; exit 1; }
done
for attempt in {1..12}; do
  if curl --fail --silent --show-error --max-time 8 \
      https://mcp.ooh.world/health/ready >/dev/null 2>&1 \
    && curl --fail --silent --show-error --max-time 8 \
      https://g.ooh.world/realms/nextcloud/.well-known/openid-configuration >/dev/null 2>&1; then
    trap - EXIT
    echo "JOURNALD_RETENTION_DEPLOYED rollback_file=$backup"
    exit 0
  fi
  sleep 5
done
echo 'Public service checks did not recover' >&2
exit 1
