from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from mcp import Client
from pydantic import AnyHttpUrl

import nextcloud_chatgpt_bridge.hosted_server as hosted
import nextcloud_chatgpt_bridge.server as core
from nextcloud_chatgpt_bridge.auth import HostedAuthConfig
from nextcloud_chatgpt_bridge.connections.models import ConnectStart
from nextcloud_chatgpt_bridge.identity import BridgeIdentity, BridgeSessionContext
from nextcloud_chatgpt_bridge.runtime import LocalSettingsResolver

pytestmark = pytest.mark.anyio


class FakeConnectionService:
    def __init__(self) -> None:
        self.started: list[tuple[str, str, str]] = []

    def begin_connection(self, *, context, base_url: str, root_path: str):
        self.started.append((context.tenant_id, base_url, root_path))
        return ConnectStart(
            flow_id="flow_1234567890123456",
            login_url=AnyHttpUrl("https://cloud.example.com/login/v2/flow/abc"),
            expires_at=datetime.now(UTC) + timedelta(minutes=20),
        )

    def poll_connection(self, *, context, flow_id: str):
        return None

    def list_connections(self, *, context):
        return []

    def update_root_path(self, **kwargs):
        raise AssertionError("not used")

    def disconnect(self, **kwargs):
        raise AssertionError("not used")

    def resolve_settings(self, **kwargs):
        raise AssertionError("not used")


class FakeHouseholdService:
    def configure_profile(self, *, context, connection_id: str, display_name: str, **kwargs):
        from nextcloud_chatgpt_bridge.household.models import HouseholdProfileSummary

        now = datetime.now(UTC)
        return HouseholdProfileSummary(
            profile_id="hh_1234567890123456",
            connection_id=connection_id,
            display_name=display_name,
            invoice_inbox_path="Household/Invoices/Inbox",
            invoice_archive_path="Household/Invoices/Archive",
            review_report_path="Household/Invoices/Reviews",
            default_currency="EUR",
            created_at=now,
            updated_at=now,
        )

    def list_profiles(self, **kwargs):
        return []

    def prepare_workspace(self, **kwargs):
        raise AssertionError("not used")

    def list_invoice_candidates(self, **kwargs):
        return []

    def review_invoice(self, **kwargs):
        raise AssertionError("not used")

    def save_invoice_review(self, **kwargs):
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


def session() -> BridgeSessionContext:
    return BridgeSessionContext(
        identity=BridgeIdentity(
            issuer="https://auth.example.com/",
            subject="user-a",
        ),
        client_id="chatgpt-client",
        scopes=frozenset({"nextcloud:use"}),
    )


async def test_hosted_server_exposes_core_and_connection_tools(monkeypatch):
    service = FakeConnectionService()
    monkeypatch.setattr(hosted, "current_session_context", session)
    mcp = hosted.create_hosted_mcp(
        connection_service=service,  # type: ignore[arg-type]
        auth_config=auth_config(),
        household_service=FakeHouseholdService(),  # type: ignore[arg-type]
    )

    try:
        async with Client(mcp) as client:
            listed = await client.list_tools()
            result = await client.call_tool(
                "begin_nextcloud_connection",
                {"base_url": "https://cloud.example.com", "root_path": "/ChatGPT"},
            )
            household = await client.call_tool(
                "configure_household_account",
                {
                    "connection_id": "nc_1234567890123456",
                    "display_name": "Our Household",
                },
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
            "configure_household_account",
            "list_household_accounts",
            "prepare_household_workspace",
            "list_household_invoices",
            "review_household_invoice",
            "save_household_invoice_review",
        } <= names
        assert result.is_error is False
        assert result.structured_content["flow_id"] == "flow_1234567890123456"
        assert "app_password" not in str(result.structured_content).lower()
        assert service.started == [
            (session().tenant_id, "https://cloud.example.com", "/ChatGPT")
        ]
        assert household.is_error is False
        assert household.structured_content["profile_id"] == "hh_1234567890123456"
    finally:
        core.configure_settings_resolver(LocalSettingsResolver())


async def test_hosted_server_marks_private_nextcloud_tools_closed_world():
    service = FakeConnectionService()
    mcp = hosted.create_hosted_mcp(
        connection_service=service,  # type: ignore[arg-type]
        auth_config=auth_config(),
    )

    try:
        async with Client(mcp) as client:
            listed = await client.list_tools()
        tools = {tool.name: tool for tool in listed.tools}
        assert tools["list_files"].annotations.read_only_hint is True
        assert tools["list_files"].annotations.destructive_hint is False
        assert tools["list_files"].annotations.open_world_hint is False
        assert tools["write_text_file"].annotations.destructive_hint is True
        assert tools["write_text_file"].annotations.open_world_hint is False
        assert tools["disconnect_nextcloud"].annotations.destructive_hint is True
        assert tools["disconnect_nextcloud"].annotations.open_world_hint is False
    finally:
        core.configure_settings_resolver(LocalSettingsResolver())


async def test_hosted_server_tool_contract_is_submission_complete():
    service = FakeConnectionService()
    mcp = hosted.create_hosted_mcp(
        connection_service=service,  # type: ignore[arg-type]
        auth_config=auth_config(),
        household_service=FakeHouseholdService(),  # type: ignore[arg-type]
    )
    expected = {
        "get_nextcloud_capabilities": (True, False, None),
        "get_nextcloud_app_accesses": (True, False, None),
        "probe_native_nextcloud_mcp": (True, False, None),
        "list_files": (True, False, None),
        "search_files": (True, False, None),
        "list_nextcloud_shares": (True, False, None),
        "get_file_info": (True, False, None),
        "read_text_file": (True, False, None),
        "download_file_base64": (True, False, None),
        "write_text_file": (False, True, False),
        "upload_file_base64": (False, True, False),
        "create_folder": (False, False, False),
        "move_file": (False, True, False),
        "delete_file": (False, True, True),
        "begin_nextcloud_connection": (False, False, False),
        "poll_nextcloud_connection": (False, False, False),
        "list_nextcloud_connections": (True, False, None),
        "set_nextcloud_root": (False, False, True),
        "disconnect_nextcloud": (False, True, False),
        "configure_household_account": (False, False, True),
        "list_household_accounts": (True, False, None),
        "prepare_household_workspace": (False, False, True),
        "list_household_invoices": (True, False, None),
        "review_household_invoice": (True, False, None),
        "save_household_invoice_review": (False, False, True),
    }

    try:
        async with Client(mcp) as client:
            listed = await client.list_tools()

        tools = {tool.name: tool for tool in listed.tools}
        assert set(tools) == set(expected)
        for name, (read_only, destructive, idempotent) in expected.items():
            tool = tools[name]
            assert tool.title
            assert tool.description
            assert tool.input_schema
            assert tool.output_schema
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is read_only
            assert tool.annotations.destructive_hint is destructive
            assert tool.annotations.open_world_hint is False
            assert tool.annotations.idempotent_hint is idempotent
    finally:
        core.configure_settings_resolver(LocalSettingsResolver())
