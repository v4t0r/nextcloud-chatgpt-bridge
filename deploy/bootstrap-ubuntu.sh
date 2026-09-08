#!/usr/bin/env bash
# Bootstrap a fresh VM only. Application deployment is a separate, verified step.
set -euo pipefail

usage() {
    printf '%s\n' \
        'Usage: sudo bash deploy/bootstrap-ubuntu.sh --install' \
        'Installs Docker Engine/Compose and prerequisites on fresh Ubuntu Server.' \
        'Does not configure domains, OAuth, firewall, SSH, or start the bridge.'
}

case "${1:-}" in
    --help|-h) usage; exit 0 ;;
    --install) ;;
    *) usage >&2; exit 2 ;;
esac
if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi
if [[ "$(uname -s)" != Linux || ! -r /etc/os-release ]]; then
    printf '%s\n' 'Run this script on the target Ubuntu VM.' >&2
    exit 1
fi
if [[ "$EUID" -ne 0 ]]; then
    printf '%s\n' 'Run with sudo on the target VM.' >&2
    exit 1
fi
# shellcheck source=/dev/null
source /etc/os-release
if [[ "${ID:-}" != ubuntu || ! "${VERSION_ID:-}" =~ ^(24\.04|26\.04)$ ]]; then
    printf '%s\n' 'Supported base systems: Ubuntu Server 24.04 or 26.04 LTS.' >&2
    exit 1
fi
if [[ "$(dpkg --print-architecture)" != amd64 ]]; then
    printf '%s\n' 'This VM bootstrap is intended for amd64.' >&2
    exit 1
fi
if [[ ! -d /run/systemd/system ]]; then
    printf '%s\n' 'A systemd-based VM is required; do not run in a container.' >&2
    exit 1
fi
for package in docker-ce docker.io docker-compose docker-compose-v2 docker-doc \
    podman-docker containerd containerd.io runc; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        printf 'Existing container package detected: %s. Inspect the host before changing it.\n' "$package" >&2
        exit 1
    fi
done
if [[ -e /etc/apt/sources.list.d/docker.sources || -e /etc/apt/sources.list.d/docker.list ]]; then
    printf '%s\n' 'Existing Docker repository configuration found; inspect before retrying.' >&2
    exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git open-vm-tools python3 python3-venv
install -m 0755 -d /etc/apt/keyrings
key_download="$(mktemp)"
trap 'rm -f -- "$key_download"' EXIT
curl --fail --show-error --silent --location --retry 3 \
    https://download.docker.com/linux/ubuntu/gpg --output "$key_download"
install -m 0644 "$key_download" /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
docker run --rm hello-world
install -d -m 0700 /var/lib/nextcloud-bridge
dpkg-query -W -f='${Package}\t${Version}\n' \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
    open-vm-tools python3 > /var/lib/nextcloud-bridge/bootstrap-packages.txt
printf '%s\n' \
    'VM prerequisites installed and Docker smoke test passed.' \
    'Package versions: /var/lib/nextcloud-bridge/bootstrap-packages.txt' \
    'Continue with docs/SINGLE_VM_DEPLOYMENT.md. OAuth and bridge are not deployed yet.'
