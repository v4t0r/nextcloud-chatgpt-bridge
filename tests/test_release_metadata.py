from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

from nextcloud_chatgpt_bridge import __version__


def test_package_versions_are_consistent():
    project_root = Path(__file__).resolve().parents[1]
    metadata = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["version"] == __version__
    assert version("nextcloud-chatgpt-bridge") == __version__


def test_release_license_is_declared_and_present():
    project_root = Path(__file__).resolve().parents[1]
    metadata = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["license"] == "Apache-2.0"
    assert (project_root / "LICENSE").is_file()
