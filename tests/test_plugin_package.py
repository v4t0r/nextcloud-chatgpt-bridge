from __future__ import annotations

import json
from pathlib import Path

import yaml

from nextcloud_chatgpt_bridge import __version__


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_codex_plugin_manifest_and_assets_are_release_ready():
    root = _project_root()
    plugin = root / "plugins" / "nextcloud-for-chatgpt-codex"
    manifest = json.loads(
        (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )

    assert manifest["name"] == "nextcloud-for-chatgpt-codex"
    assert manifest["version"] == __version__
    assert manifest["license"] == "Apache-2.0"
    assert manifest["homepage"].startswith("https://")
    assert manifest["repository"].startswith("https://")
    assert manifest["interface"]["displayName"] == "Nextcloud for ChatGPT & Codex"

    for key in ("composerIcon", "logo", "logoDark"):
        asset = plugin / manifest["interface"][key]
        assert asset.is_file()
        assert asset.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_codex_plugin_skill_has_valid_front_matter():
    root = _project_root()
    skill = (
        root
        / "plugins"
        / "nextcloud-for-chatgpt-codex"
        / "skills"
        / "nextcloud-workspace"
        / "SKILL.md"
    )
    contents = skill.read_text(encoding="utf-8")
    _, front_matter, body = contents.split("---", 2)
    metadata = yaml.safe_load(front_matter)

    assert metadata["name"] == "nextcloud-workspace"
    assert isinstance(metadata["description"], str)
    assert "Nextcloud" in metadata["description"]
    assert "Never ask the user to paste" in body
    assert "Never approve, book, pay" in body


def test_personal_marketplace_points_to_the_release_plugin():
    root = _project_root()
    marketplace = json.loads(
        (root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
    )
    entry = next(
        plugin
        for plugin in marketplace["plugins"]
        if plugin["name"] == "nextcloud-for-chatgpt-codex"
    )

    source = entry["source"]
    assert source["source"] == "local"
    assert (root / source["path"]).is_dir()
    assert entry["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
