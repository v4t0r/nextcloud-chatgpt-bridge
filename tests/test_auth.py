from __future__ import annotations

import time
from types import SimpleNamespace

import jwt
import pytest
from pydantic import ValidationError

from nextcloud_chatgpt_bridge.auth import HostedAuthConfig, OIDCTokenVerifier, build_mcp_auth


def config(**overrides) -> HostedAuthConfig:
    values = {
        "BRIDGE_AUTH_ISSUER_URL": "https://auth.example.com/",
        "BRIDGE_AUTH_JWKS_URL": "https://auth.example.com/.well-known/jwks.json",
        "BRIDGE_RESOURCE_SERVER_URL": "https://bridge.example.com/mcp",
        "BRIDGE_AUTH_AUDIENCE": "https://bridge.example.com/mcp",
        "BRIDGE_AUTH_REQUIRED_SCOPES": "nextcloud:use nextcloud:files",
        "BRIDGE_AUTH_ALLOWED_ALGORITHMS": "RS256",
    }
    values.update(overrides)
    return HostedAuthConfig(**values)


def test_hosted_auth_requires_https():
    with pytest.raises(ValidationError):
        config(BRIDGE_AUTH_JWKS_URL="http://auth.example.com/jwks.json")


def test_hosted_auth_rejects_shared_secret_jwt_algorithms():
    with pytest.raises(ValidationError, match="shared-secret"):
        config(BRIDGE_AUTH_ALLOWED_ALGORITHMS="HS256")


def test_mcp_auth_settings_publish_issuer_resource_and_scopes():
    auth, verifier = build_mcp_auth(config())

    assert str(auth.issuer_url) == "https://auth.example.com/"
    assert str(auth.resource_server_url) == "https://bridge.example.com/mcp"
    assert auth.required_scopes == ["nextcloud:use", "nextcloud:files"]
    assert isinstance(verifier, OIDCTokenVerifier)


@pytest.mark.anyio
async def test_verifier_maps_verified_subject_client_scopes_and_audience(monkeypatch):
    verifier = OIDCTokenVerifier(config())
    claims = {
        "iss": "https://auth.example.com/",
        "aud": "https://bridge.example.com/mcp",
        "sub": "user-123",
        "client_id": "chatgpt-client",
        "scope": "nextcloud:use nextcloud:files extra",
        "iat": int(time.time()) - 1,
        "exp": int(time.time()) + 600,
    }
    monkeypatch.setattr(verifier, "_decode", lambda token: claims)

    result = await verifier.verify_token("signed-token")

    assert result is not None
    assert result.subject == "user-123"
    assert result.client_id == "chatgpt-client"
    assert result.resource == "https://bridge.example.com/mcp"
    assert set(result.scopes) == {"nextcloud:use", "nextcloud:files", "extra"}
    assert result.claims is not None
    assert "exp" not in result.claims


@pytest.mark.anyio
async def test_verifier_rejects_missing_required_scope(monkeypatch):
    verifier = OIDCTokenVerifier(config())
    monkeypatch.setattr(
        verifier,
        "_decode",
        lambda token: {
            "iss": "https://auth.example.com/",
            "aud": "https://bridge.example.com/mcp",
            "sub": "user-123",
            "azp": "chatgpt-client",
            "scope": "nextcloud:use",
            "iat": int(time.time()) - 1,
            "exp": int(time.time()) + 600,
        },
    )

    assert await verifier.verify_token("signed-token") is None


@pytest.mark.anyio
async def test_verifier_sanitizes_invalid_jwt_failures(monkeypatch):
    verifier = OIDCTokenVerifier(config())

    def fail(token):
        raise jwt.InvalidAudienceError("internal detail")

    monkeypatch.setattr(verifier, "_decode", fail)
    assert await verifier.verify_token("bad-token") is None


def test_decode_pins_signature_algorithm_issuer_and_audience(monkeypatch):
    verifier = OIDCTokenVerifier(config())
    seen: dict[str, object] = {}

    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token: str):
            seen["token"] = token
            return SimpleNamespace(key="public-key")

    def fake_decode(token, **kwargs):
        seen["decode_token"] = token
        seen.update(kwargs)
        return {
            "iss": "https://auth.example.com/",
            "aud": "https://bridge.example.com/mcp",
            "sub": "user-123",
            "client_id": "client",
            "scope": "nextcloud:use nextcloud:files",
            "iat": int(time.time()) - 1,
            "exp": int(time.time()) + 600,
        }

    verifier.jwks_client = FakeJWKClient()  # type: ignore[assignment]
    monkeypatch.setattr(jwt, "decode", fake_decode)

    verifier._decode("signed-token")

    assert seen["key"] == "public-key"
    assert seen["algorithms"] == ["RS256"]
    assert seen["audience"] == "https://bridge.example.com/mcp"
    assert seen["issuer"] == "https://auth.example.com/"
    options = seen["options"]
    assert options["verify_signature"] is True
    assert options["verify_aud"] is True
    assert options["verify_iss"] is True
