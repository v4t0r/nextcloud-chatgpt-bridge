"""Build the existing OpenAI directory package without credentials or local files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PACKAGE_NAME = "app-6a91e995840081918f48e8cd5d8cefff"
PACKAGE_VERSION = "1.0.1"


def build_package(root: Path, output: Path) -> Path:
    source = root / "plugins" / "nextcloud-for-chatgpt-codex"
    legacy = json.loads((source / ".codex-plugin" / "plugin.json").read_text("utf-8"))
    interface = legacy["interface"]
    for key in ("composerIcon", "logo", "logoDark"):
        interface[key] = "./" + interface[key].removeprefix("./")
    interface["defaultPrompt"] = [
        "Show the files at the top level of my Nextcloud workspace.",
        "Find documents with household in the filename.",
        "Review the newest household invoice, but do not approve or pay it.",
    ]
    manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        **{key: legacy[key] for key in (
            "description", "author", "homepage", "repository", "license", "keywords"
        )},
        "extensions": {"com.openai": {"interface": interface}},
    }
    files = {
        "plugin.json": (json.dumps(manifest, indent=2) + "\n").encode(),
        "mcp.json": (source / "mcp.json").read_bytes(),
        "skills/nextcloud-workspace/SKILL.md": (
            source / "skills" / "nextcloud-workspace" / "SKILL.md"
        ).read_bytes(),
        "assets/nextcloud-bridge-mark.png": (
            source / "assets" / "nextcloud-bridge-mark.png"
        ).read_bytes(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, contents in sorted(files.items()):
            entry = ZipInfo(name, date_time=(2026, 10, 17, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, contents)
    return output


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "dist" / f"{PACKAGE_NAME}-{PACKAGE_VERSION}.zip")
    args = parser.parse_args()
    print(build_package(root, args.output))
