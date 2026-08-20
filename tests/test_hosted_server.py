from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from mcp import Client
from pydantic import AnyHttpUrl

import nextcloud_chatgpt_bridge.hosted_server as hosted
import nextcloud_chatgpt_bridge.server as core
from nextcloud_chatgpt_bridge.auth import HostedAuthConfig
from nextcloud_chatgpt_bridge.connections.models import ConnectStart, ConnectionSummary
from nextcloud_chatgpt_bridge.runtime import LocalSettingsResolver

pytestmark = pytest.mark.anyio


class FakeConnectionService:
    def __init__(self) -> None:
        self.started: list[tuple[str, str, str]] = []

    def begin_connection(self, *, owner_subject: str, base_url: str, root_path: str):
        self.started.append((owner_subject, base_url, root_path))
        return ConnectStart(
            flow_id="flow_1234567890123456",
            login_url=AnyHttpUrl("https://cloud.example.com/login/v2/flow/abc"),
            expires_at=datetime.now(UTC) + timedelta(minutes=20),
        )

    def poll_connection(self, *, owner_subject: str, flow_id: str):
        return None

    def list_connections(self, *, owner_subject: str):
        return []

    def update_root_path(self, **kwargs):
        raise AssertionError("not used")

    def disconnect(self, **kwargs):
        raise AssertionError("not used")

    def resolve_settings(self, **kwargs):
        raise AssertionError("not used")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def auth_config() -> HostedAuthConfig:
    return HostedAuthConfig(
        BRIDGE_AUTH_ISSUER_URL="https://auth.example.com/",
        BRIDGE_AUTH_JWKS_URL="https://auth.example.com/.well-known/jwks.json",
        BRIDGE_RESOURCE_SERVER_URL="https://bridge.example.com/mcp",
        BRIDGE_AUTH_AUDIENCE="https://bridge.example.com/mcp",
        BRIDGE_AUTH_REQUIRED_SCOPES="nextcloud:use",
    )


async def test_hosted_server_exposes_core_and_connection_tools(monkeypatch):
    service = FakeConnectionService()
    monkeypatch.setattr(hosted, "current_oauth_subject", lambda: "user-a")
    mcp = hosted.create_hosted_mcp(
        connection_service=service,  # type: ignore[arg-type]
        auth_config=auth_config(),
    )

    try:
        async with Client(mcp) as client:
            listed = await client.list_tools()
            result = await client.call_tool(
                "begin_nextcloud_connection",
                {"base_url": "https://cloud.example.com", "root_path": "/ChatGPT"},
            )

        names = {tool.name for tool in listed.tools}
        assert {
            "list_files",
            "write_text_file",
            "begin_nextcloud_connection",
            "poll_nextcloud_connection",
            "list_nextcloud_connections",
            "set_nextcloud_root",
            "disconnect_nextcloud",
        } <= names
        assert result.is_error is False
        assert result.structured_content["flow_id"] == "flow_1234567890123456"
        assert "app_password" not in str(result.structured_content).lower()
        assert service.started == [("user-a", "https://cloud.example.com", "/ChatGPT")]
    finally:
        core.configure_settings_resolver(LocalSettingsResolver())


async def test_hosted_server_marks_external_file_tools_open_world():
    service = FakeConnectionService()
    mcp = hosted.create_hosted_mcp(
        connection_service=service,  # type: ignore[arg-type]
        auth_config=auth_config(),
    )

    try:
        async with Client(mcp) as client:
            listed = await client.list_tools()
        tools = {tool.name: tool for tool in listed.tools}
        assert tools["list_files"].annotations.open_world_hint is True
        assert tools["write_text_file"].annotations.destructive_hint is True
        assert tools["disconnect_nextcloud"].annotations.destructive_hint is True
    finally:
        core.configure_settings_resolver(LocalSettingsResolver())
