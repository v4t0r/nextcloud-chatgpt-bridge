from __future__ import annotations

from dataclasses import dataclass

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from nextcloud_chatgpt_bridge.config import Settings

_MAX_REPORTED_TOOLS = 200
_MAX_TOOL_NAME_LENGTH = 128


class NativeMCPError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class NativeMCPProbeResult:
    endpoint: str
    protocol_version: str | None
    tool_names: tuple[str, ...]
    tools_truncated: bool


def context_agent_mcp_url(settings: Settings) -> str:
    base = str(settings.nextcloud_base_url).rstrip("/")
    return f"{base}/index.php/apps/app_api/proxy/context_agent/mcp/"


def _safe_tool_names(tools: list[object]) -> tuple[tuple[str, ...], bool]:
    names: list[str] = []
    for tool in tools[: _MAX_REPORTED_TOOLS + 1]:
        raw = getattr(tool, "name", "")
        name = str(raw).strip()[:_MAX_TOOL_NAME_LENGTH]
        if name:
            names.append(name)

    truncated = len(names) > _MAX_REPORTED_TOOLS or len(tools) > _MAX_REPORTED_TOOLS
    return tuple(names[:_MAX_REPORTED_TOOLS]), truncated


async def probe_context_agent_mcp(settings: Settings) -> NativeMCPProbeResult:
    """Probe Nextcloud Context Agent MCP without invoking any remote tools."""
    endpoint = context_agent_mcp_url(settings)
    headers = {
        "Authorization": f"Bearer {settings.nextcloud_app_password.get_secret_value()}",
    }

    # Redirects are intentionally disabled so the bearer token is never forwarded to a
    # different target. The documented Nextcloud endpoint includes its trailing slash.
    try:
        async with httpx2.AsyncClient(
            headers=headers,
            verify=settings.nextcloud_verify_tls,
            follow_redirects=False,
            timeout=httpx2.Timeout(15.0, read=30.0),
        ) as http_client:
            transport = streamable_http_client(
                endpoint,
                http_client=http_client,
                terminate_on_close=False,
            )
            async with Client(transport) as client:
                listed = await client.list_tools()
                names, truncated = _safe_tool_names(list(listed.tools))
                protocol = getattr(client, "protocol_version", None)
                return NativeMCPProbeResult(
                    endpoint=endpoint,
                    protocol_version=str(protocol) if protocol else None,
                    tool_names=names,
                    tools_truncated=truncated,
                )
    except Exception as exc:
        # Do not expose HTTP response bodies, bearer tokens, internal proxy details or
        # exception reprs to an MCP caller. The original exception remains chained for logs.
        raise NativeMCPError("Nextcloud Context Agent MCP probe failed") from exc
