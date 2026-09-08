"""Generate first-install configuration outside the source tree, without printing secrets."""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import os
import re
import secrets
from pathlib import Path


def hostname(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value) or "." not in value:
        raise argparse.ArgumentTypeError("Use a lowercase DNS hostname, without scheme or path")
    return value


def write_new(path: Path, content: str, mode: int = 0o600) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--vm-ip", type=ipaddress.IPv4Address, required=True)
    parser.add_argument("--npm-ip", type=ipaddress.IPv4Address, required=True)
    parser.add_argument("--mcp-domain", type=hostname, required=True)
    parser.add_argument("--auth-domain", type=hostname, required=True)
    parser.add_argument("--website", required=True)
    parser.add_argument("--keycloak-image", required=True)
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("Run on the target Linux VM")
    if not args.website.startswith("https://") or any(c in args.website for c in "\r\n$# "):
        parser.error("Website must be an HTTPS URL without environment-file metacharacters")
    if not re.fullmatch(r"quay\.io/keycloak/keycloak:(\d+\.){2}\d+(?:@sha256:[a-f0-9]{64})?", args.keycloak_image):
        parser.error("Provide an exact Keycloak release tag, optionally with digest")
    source = Path(__file__).resolve().parents[1]
    runtime = args.runtime_dir.resolve()
    if runtime.is_relative_to(source) or any(c in str(runtime) for c in "\r\n$# "):
        parser.error("Runtime must be outside the repository in a path without special characters")
    if runtime.exists():
        parser.error("Runtime path already exists; inspect it rather than overwriting configuration")
    runtime.mkdir(mode=0o700, parents=True)
    secret_dir = runtime / "secrets"
    secret_dir.mkdir(mode=0o700)
    # Docker mounts individual files; 0444 allows non-root container UIDs to read them.
    # The enclosing host directories stay 0700 and prevent access by other host users.
    for name in ("database-password.txt", "auth-database-password.txt", "auth-admin-password.txt", "auth-client-secret.txt"):
        write_new(secret_dir / name, secrets.token_urlsafe(48) + "\n", 0o444)
        (secret_dir / name).chmod(0o444)
    write_new(secret_dir / "credential-keyring.json", json.dumps({"primary": base64.b64encode(secrets.token_bytes(32)).decode("ascii")}) + "\n", 0o444)
    (secret_dir / "credential-keyring.json").chmod(0o444)
    issuer = f"https://{args.auth_domain}/realms/nextcloud"
    website = args.website.rstrip("/")
    values = {
        "PUBLIC_DOMAIN": args.mcp_domain,
        "AUTH_DOMAIN": args.auth_domain,
        "VM_BIND_IP": str(args.vm_ip),
        "NPM_PROXY_IP": str(args.npm_ip),
        "KEYCLOAK_IMAGE": args.keycloak_image,
        "BRIDGE_PRIVATE_SUBNET": "172.30.83.0/28",
        "BRIDGE_DYNAMIC_RANGE": "172.30.83.0/29",
        "BRIDGE_EDGE_IP": "172.30.83.14",
        "AUTH_PRIVATE_SUBNET": "172.30.84.0/28",
        "AUTH_DYNAMIC_RANGE": "172.30.84.0/29",
        "AUTH_EDGE_IP": "172.30.84.14",
        "BRIDGE_RESOURCE_SERVER_URL": f"https://{args.mcp_domain}/mcp",
        "BRIDGE_AUTH_ISSUER_URL": issuer,
        "BRIDGE_AUTH_JWKS_URL": issuer + "/protocol/openid-connect/certs",
        "BRIDGE_AUTH_DISCOVERY_URL": issuer + "/.well-known/openid-configuration",
        "BRIDGE_AUTH_AUDIENCE": f"https://{args.mcp_domain}/mcp",
        "BRIDGE_AUTH_REQUIRED_SCOPES": "nextcloud:use",
        "BRIDGE_AUTH_ALLOWED_ALGORITHMS": "RS256",
        "BRIDGE_AUTH_CLIENT_MODE": "predefined",
        "BRIDGE_AUTH_REQUIRE_USERINFO": "false",
        "BRIDGE_WEBSITE_URL": website,
        "BRIDGE_SUPPORT_URL": website + "/support",
        "BRIDGE_PRIVACY_URL": website + "/privacy",
        "BRIDGE_TERMS_URL": website + "/terms",
        "BRIDGE_DB_PASSWORD_FILE": str(secret_dir / "database-password.txt"),
        "BRIDGE_KEYRING_FILE": str(secret_dir / "credential-keyring.json"),
        "AUTH_DB_PASSWORD_FILE": str(secret_dir / "auth-database-password.txt"),
        "AUTH_ADMIN_PASSWORD_FILE": str(secret_dir / "auth-admin-password.txt"),
        "AUTH_CLIENT_SECRET_FILE": str(secret_dir / "auth-client-secret.txt"),
        "OPENAI_APPS_CHALLENGE_TOKEN": "",
    }
    template = (source / "deploy" / ".env.production.example").read_text(encoding="utf-8")
    result: list[str] = []
    written: set[str] = set()
    for line in template.splitlines():
        key = line.split("=", 1)[0]
        if key in values and "=" in line:
            line = f"{key}={values[key]}"
            written.add(key)
        result.append(line)
    result.extend(f"{key}={value}" for key, value in values.items() if key not in written)
    write_new(runtime / "production.env", "\n".join(result) + "\n")
    print("Runtime configuration created; no secret values printed. OAuth client remains disabled.")


if __name__ == "__main__":
    main()
