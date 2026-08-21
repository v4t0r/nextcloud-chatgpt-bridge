from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
