from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "posix", reason="Linux VM provisioning")


def run_init(runtime: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed trusted test script, no shell
        [
            sys.executable,
            str(ROOT / "deploy" / "init-npm-runtime.py"),
            "--runtime-dir", str(runtime),
            "--vm-ip", "192.0.2.84",
            "--npm-ip", "192.0.2.111",
            "--mcp-domain", "mcp.example.com",
            "--auth-domain", "auth.example.com",
            "--website", "https://www.example.com",
            "--keycloak-image", "quay.io/keycloak/keycloak:26.7.3",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_runtime_secrets_are_private_and_never_printed(tmp_path: Path):
    runtime = tmp_path / "runtime"
    result = run_init(runtime)
    assert result.returncode == 0, result.stderr
    assert runtime.stat().st_mode & 0o777 == 0o700
    assert (runtime / "secrets").stat().st_mode & 0o777 == 0o700
    environment = (runtime / "production.env").read_text()
    assert (runtime / "production.env").stat().st_mode & 0o777 == 0o600
    assert "BRIDGE_AUTH_CLIENT_MODE=predefined" in environment
    assert "BRIDGE_AUTH_AUDIENCE=https://mcp.example.com/mcp" in environment
    for secret in (runtime / "secrets").iterdir():
        value = secret.read_text().strip()
        assert value and value not in result.stdout + result.stderr + environment
        assert secret.stat().st_mode & 0o777 == 0o444


def test_reinitialization_does_not_rotate_or_overwrite_secrets(tmp_path: Path):
    runtime = tmp_path / "runtime"
    assert run_init(runtime).returncode == 0
    before = {file.name: file.read_bytes() for file in (runtime / "secrets").iterdir()}
    second = run_init(runtime)
    assert second.returncode != 0
    assert "already exists" in second.stderr
    assert before == {file.name: file.read_bytes() for file in (runtime / "secrets").iterdir()}
