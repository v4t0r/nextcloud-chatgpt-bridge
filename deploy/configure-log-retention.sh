#!/usr/bin/env bash
# Host-wide journal retention for production container and system logs.
set -Eeuo pipefail
[[ "$(id -u)" == 0 ]] || { echo 'Run with sudo' >&2; exit 1; }

install -d -m 755 /etc/systemd/journald.conf.d
cat >/etc/systemd/journald.conf.d/nextcloud-bridge-retention.conf <<'EOF'
[Journal]
Storage=persistent
MaxRetentionSec=7day
SystemMaxUse=256M
RuntimeMaxUse=64M
EOF
chmod 644 /etc/systemd/journald.conf.d/nextcloud-bridge-retention.conf
systemctl restart systemd-journald
journalctl --rotate
journalctl --vacuum-time=7d
systemd-analyze cat-config systemd/journald.conf | grep -E '^(Storage|MaxRetentionSec|SystemMaxUse|RuntimeMaxUse)='
echo JOURNAL_RETENTION_CONFIGURED
