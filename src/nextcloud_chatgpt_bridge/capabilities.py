from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from nextcloud_chatgpt_bridge.config import Settings

_MAX_CAPABILITY_NODES = 10_000


class CapabilityReport(BaseModel):
    nextcloud_version: str | None = None
    version_major: int | None = None
    version_minor: int | None = None
    version_micro: int | None = None
    capability_groups: list[str]
    app_api_hint: bool
    assistant_hint: bool
    context_agent_hint: bool
    context_agent_mcp_url: str


def _all_keys(value: Any) -> set[str]:
    """Collect nested capability keys without recursive-stack exposure."""
    keys: set[str] = set()
    stack: list[Any] = [value]
    visited = 0

    while stack:
        current = stack.pop()
        visited += 1
        if visited > _MAX_CAPABILITY_NODES:
            break

        if isinstance(current, dict):
            for key, child in current.items():
                keys.add(str(key).lower())
                if isinstance(child, (dict, list)):
                    stack.append(child)
        elif isinstance(current, list):
            for child in current:
                if isinstance(child, (dict, list)):
                    stack.append(child)
                elif isinstance(child, str):
                    keys.add(child.lower())

    return keys


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def build_capability_report(settings: Settings, data: dict[str, Any]) -> CapabilityReport:
    version = data.get("version") if isinstance(data.get("version"), dict) else {}
    capabilities = data.get("capabilities") if isinstance(data.get("capabilities"), dict) else {}
    groups = sorted(str(key) for key in capabilities)
    keys = _all_keys(capabilities)

    base = str(settings.nextcloud_base_url).rstrip("/")
    return CapabilityReport(
        nextcloud_version=str(version.get("string")) if version.get("string") else None,
        version_major=_as_int(version.get("major")),
        version_minor=_as_int(version.get("minor")),
        version_micro=_as_int(version.get("micro")),
        capability_groups=groups,
        app_api_hint="app_api" in keys,
        assistant_hint="assistant" in keys,
        context_agent_hint="context_agent" in keys,
        context_agent_mcp_url=(
            f"{base}/index.php/apps/app_api/proxy/context_agent/mcp/"
        ),
    )
