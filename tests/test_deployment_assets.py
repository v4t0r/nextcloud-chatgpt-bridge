from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_email_scope_uses_real_verification_status_and_preserves_oauth_boundaries():
    realm = json.loads((ROOT / "deploy/keycloak/nextcloud-realm.json").read_text())
    email = next(scope for scope in realm["clientScopes"] if scope["name"] == "email")
    mappers = {mapper["config"]["claim.name"]: mapper for mapper in email["protocolMappers"]}
    verified = mappers["email_verified"]
    assert verified["protocolMapper"] == "oidc-usermodel-property-mapper"
    assert verified["config"]["user.attribute"] == "emailVerified"
    assert verified["config"]["userinfo.token.claim"] == "true"
    assert verified["config"]["jsonType.label"] == "boolean"
    assert mappers["email"]["config"]["userinfo.token.claim"] == "true"
    client = realm["clients"][0]
    assert "email" in client["defaultClientScopes"]
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert client["publicClient"] is False
    assert client["directAccessGrantsEnabled"] is False
    assert client["enabled"] is False  # fresh installations require an exact callback first
    assert client["redirectUris"] == []


def _example_keys(content: str) -> set[str]:
    return {
        line.split("=", 1)[0]
        for line in content.splitlines()
        if line and not line.startswith("#") and "=" in line
    }


def test_production_environment_example_covers_compose_variables_without_secrets():
    example = (ROOT / "deploy" / ".env.production.example").read_text(encoding="utf-8")
    compose = (ROOT / "deploy" / "compose.production.yml").read_text(encoding="utf-8")

    compose_variables = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", compose))
    assert compose_variables <= _example_keys(example)
    assert "replace-with" not in example
    assert "sk-" not in example
    assert "NEXTCLOUD_APP_PASSWORD" not in example


def test_documented_no_store_modes_link_to_official_openai_guidance():
    document = (ROOT / "docs" / "DEPLOYMENT_MODES.md").read_text(encoding="utf-8")

    assert "does not depend on publication" in document
    assert "https://learn.chatgpt.com/docs/extend/mcp" in document
    assert "https://developers.openai.com/plugins/deploy/connect-chatgpt" in document
    assert "https://developers.openai.com/api/docs/guides/secure-mcp-tunnels" in document
