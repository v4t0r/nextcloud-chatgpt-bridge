#!/usr/bin/env bash
# Encrypted, rootless backup of the two production databases and recovery files.
set -Eeuo pipefail
umask 077

runtime="${BRIDGE_RUNTIME_DIR:-$HOME/nextcloud-runtime}"
backup_dir="${BRIDGE_BACKUP_DIR:-$runtime/backups}"
key_file="${BRIDGE_BACKUP_KEY_FILE:-$HOME/.config/nextcloud-bridge-backup/passphrase}"
lock_file="$runtime/.backup.lock"

[[ -f "$runtime/production.env" && -d "$runtime/secrets" ]] || {
  echo 'Backup input missing' >&2
  exit 1
}
[[ -f "$key_file" ]] || {
  echo 'Backup encryption key missing' >&2
  exit 1
}
[[ "$(stat -c %a "$key_file")" == 600 ]] || {
  echo 'Backup encryption key must have mode 0600' >&2
  exit 1
}
mkdir -p -m 700 "$backup_dir"
[[ "$(stat -c %a "$backup_dir")" == 700 ]] || {
  echo 'Backup directory must have mode 0700' >&2
  exit 1
}

exec 9>"$lock_file"
flock -n 9 || {
  echo 'Another backup is already running' >&2
  exit 1
}

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
partial="$(mktemp -d "$backup_dir/.partial.XXXXXXXX")"
cleanup() {
  local status=$?
  if (( status != 0 )); then
    logger -p user.err -t nextcloud-bridge-backup "BACKUP_FAILED exit=$status"
  fi
  rm -rf -- "$partial"
}
trap cleanup EXIT

encrypt_stream() {
  local target="$1"
  gpg --batch --yes --pinentry-mode loopback \
    --passphrase-file "$key_file" --cipher-algo AES256 \
    --symmetric --output "$partial/$target.gpg"
}

docker exec -u postgres nextcloud-chatgpt-bridge-database-1 \
  pg_dump -U bridge -d bridge --format=custom --no-owner --no-privileges \
  | encrypt_stream bridge.pgcustom
docker exec -u postgres nextcloud-chatgpt-bridge-auth_database-1 \
  pg_dump -U keycloak -d keycloak --format=custom --no-owner --no-privileges \
  | encrypt_stream keycloak.pgcustom
tar -C "$runtime" -cf - production.env secrets \
  | encrypt_stream recovery-files.tar

# Verify authenticated decryption and dump format without writing plaintext to disk.
for name in bridge keycloak; do
  header="$(gpg --batch --yes --pinentry-mode loopback --passphrase-file "$key_file" \
    --decrypt "$partial/$name.pgcustom.gpg" 2>/dev/null | head -c 5 || true)"
  [[ "$header" == PGDMP ]] || { echo 'Invalid PostgreSQL archive' >&2; exit 1; }
  gpg --batch --yes --pinentry-mode loopback --passphrase-file "$key_file" \
    --decrypt "$partial/$name.pgcustom.gpg" >/dev/null 2>&1
done
gpg --batch --yes --pinentry-mode loopback --passphrase-file "$key_file" \
  --decrypt "$partial/recovery-files.tar.gpg" 2>/dev/null | tar -tf - >/dev/null

printf '%s\n' "$stamp" >"$partial/complete"
mv -- "$partial" "$backup_dir/$stamp"
trap - EXIT

# The daily schedule removes completed backups as they cross the 30-day age.
find "$backup_dir" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' \
  -mmin +43200 -exec rm -rf -- {} +
echo "BACKUP_OK $stamp"
