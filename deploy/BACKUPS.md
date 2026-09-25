# Production bridge backups

`backup-daily.sh` runs as the `deploy` user at 03:15 UTC through
`install-backup-cron.sh`. It streams custom-format dumps of the bridge and
Keycloak PostgreSQL databases, plus `production.env` and the runtime `secrets`
directory, directly into GPG AES-256 encrypted files. Successful runs are
marked by a `complete` file. Completed sets older than 30 days are removed on
the next daily run.

The runtime paths on the current VM are:

- Backups: `/home/deploy/nextcloud-runtime/backups` (mode 0700)
- Encryption passphrase:
  `/home/deploy/.config/nextcloud-bridge-backup/passphrase` (mode 0600)
- Script: `/home/deploy/nextcloud-runtime/backup-daily.sh`

The passphrase is intentionally excluded from the recovery archive. Keep a
separate, access-controlled copy of both the passphrase and the encrypted
archives on a different host before relying on this for VM-loss recovery. No
off-host copy is configured yet.

To check a completed set without exposing plaintext files, decrypt each
archive to a pipe and verify the two database headers with `PGDMP`, a full
decryption pass, and the recovery tar listing. This is a structural check;
restoration into disposable PostgreSQL instances should be tested before
claiming full disaster-recovery readiness. Never print the passphrase or
recovery-file contents to a terminal, log, or support request.

For restoration, stop public traffic, select a completed set, restore each
database with `gpg --decrypt ... | pg_restore ...` into empty compatible
PostgreSQL databases, then restore `production.env` and `secrets` from the
encrypted tar into a protected runtime directory. Validate the OAuth issuer,
MCP health, and public routes before reopening traffic. The repository's
normal deployment procedure is still required for service images and Compose
files; these archives contain data and private runtime configuration, not the
application source.
