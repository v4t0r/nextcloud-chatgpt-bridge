from __future__ import annotations

import json
import runpy
from pathlib import Path
from zipfile import ZipFile

import yaml

from nextcloud_chatgpt_bridge import __version__


def test_submission_zip_contains_authenticated_mcp_and_preserves_directory_identity(tmp_path):
    root = _project_root()
    builder = runpy.run_path(str(root / "scripts" / "build_submission.py"))
    archive = builder["build_package"](root, tmp_path / "submission.zip")
    with ZipFile(archive) as package:
        assert set(package.namelist()) == {
            "plugin.json", "mcp.json", "assets/nextcloud-bridge-mark.png",
            "skills/nextcloud-workspace/SKILL.md",
        }
        manifest = json.loads(package.read("plugin.json"))
        assert manifest["name"] == "app-6a91e995840081918f48e8cd5d8cefff"
        assert manifest["version"] == "1.0.1"
        assert manifest["extensions"]["com.openai"]["interface"]["developerName"] == "Jens Zimmermann"
        server = json.loads(package.read("mcp.json"))["mcpServers"]["nextcloud"]
        assert server["url"] == "https://mcp.ooh.world/mcp"
        auth = server["extensions"]["com.openai"]["auth"]
        assert auth["type"] == "oauth"
        assert auth["client"] == {
            "mode": "provided", "clientId": "nextcloud-chatgpt",
            "tokenEndpointAuthMethod": "client_secret_post",
        }
        assert "nextcloud:use" in auth["baseScopes"]
        assert "clientSecret" not in package.read("mcp.json").decode()
    second = builder["build_package"](root, tmp_path / "second.zip")
    assert archive.read_bytes() == second.read_bytes()


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
