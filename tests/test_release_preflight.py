from __future__ import annotations

from nextcloud_chatgpt_bridge.release_preflight import (
    ReleasePreflightConfig,
    validate_oauth_metadata,
    validate_resource_metadata,
)


def config(**overrides) -> ReleasePreflightConfig:
    values = {
        "BRIDGE_RESOURCE_SERVER_URL": "https://mcp.example.com/mcp",
        "BRIDGE_AUTH_ISSUER_URL": "https://auth.example.com",
        "BRIDGE_AUTH_DISCOVERY_URL": "https://auth.example.com/.well-known/openid-configuration",
        "BRIDGE_AUTH_REQUIRED_SCOPES": "nextcloud:use",
        "BRIDGE_AUTH_CLIENT_MODE": "cimd",
        "BRIDGE_WEBSITE_URL": "https://www.example.com",
        "BRIDGE_SUPPORT_URL": "https://www.example.com/support",
        "BRIDGE_PRIVACY_URL": "https://www.example.com/privacy",
        "BRIDGE_TERMS_URL": "https://www.example.com/terms",
    }
    values.update(overrides)
    return ReleasePreflightConfig(**values)


def test_resource_metadata_matches_exact_resource_issuer_and_scope():
    checks = validate_resource_metadata(
        {
            "resource": "https://mcp.example.com/mcp",
            "authorization_servers": ["https://auth.example.com"],
            "scopes_supported": ["nextcloud:use"],
        },
        config(),
    )
    assert all(check.passed for check in checks)


def test_oauth_metadata_accepts_cimd_pkce_and_required_scope():
    checks = validate_oauth_metadata(
        {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "code_challenge_methods_supported": ["S256"],
            "client_id_metadata_document_supported": True,
            "token_endpoint_auth_methods_supported": ["none", "private_key_jwt"],
            "scopes_supported": ["nextcloud:use"],
        },
        config(),
    )
    assert all(check.passed for check in checks)


def test_oauth_metadata_rejects_missing_pkce_and_client_registration():
    checks = validate_oauth_metadata(
        {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "code_challenge_methods_supported": [],
            "token_endpoint_auth_methods_supported": [],
            "scopes_supported": ["nextcloud:use"],
        },
        config(),
    )
    failed = {check.name for check in checks if not check.passed}
    assert failed == {"oauth.pkce_s256", "oauth.client_registration"}


def test_empty_domain_challenge_is_disabled():
    assert config(OPENAI_APPS_CHALLENGE_TOKEN="").challenge_token is None
