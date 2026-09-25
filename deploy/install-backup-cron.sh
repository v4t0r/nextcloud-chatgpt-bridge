#!/usr/bin/env bash
# Install the daily encrypted backup for the deployment user, preserving other jobs.
set -Eeuo pipefail
job='15 3 * * * /home/deploy/nextcloud-runtime/backup-daily.sh 2>&1 | /usr/bin/logger -t nextcloud-bridge-backup # nextcloud-bridge-backup'
temporary="$(mktemp)"
trap 'rm -f -- "$temporary"' EXIT
crontab -l 2>/dev/null >"$temporary" || true
if ! grep -Fq '# nextcloud-bridge-backup' "$temporary"; then
  printf '%s\n' "$job" >>"$temporary"
  crontab "$temporary"
fi
crontab -l | grep -F '# nextcloud-bridge-backup'
