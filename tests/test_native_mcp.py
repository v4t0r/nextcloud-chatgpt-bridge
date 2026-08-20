from __future__ import annotations

from types import SimpleNamespace

import pytest

from nextcloud_chatgpt_bridge.config import Settings
import nextcloud_chatgpt_bridge.providers.native_mcp as native_mcp

pytestmark = pytest.mark.anyio


def settings() -> Settings:
    return Settings(
        NEXTCLOUD_BASE_URL="https://cloud.example.com",
        NEXTCLOUD_USERNAME="bridge-user",
        NEXTCLOUD_APP_PASSWORD="test-app-password",  # noqa: S106
        NEXTCLOUD_ROOT_PATH="/ChatGPT",
        NEXTCLOUD_VERIFY_TLS=True,
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_context_agent_endpoint_is_derived_from_configured_base_url():
    assert native_mcp.context_agent_mcp_url(settings()) == (
        "https://cloud.example.com/index.php/apps/app_api/proxy/context_agent/mcp/"
    )


def test_safe_tool_names_are_bounded():
    tools = [SimpleNamespace(name=f"tool-{index}-" + "x" * 200) for index in range(205)]
    names, truncated = native_mcp._safe_tool_names(tools)

    assert len(names) == 200
    assert truncated is True
    assert all(len(name) <= 128 for name in names)


async def test_probe_uses_bearer_auth_without_redirects_and_only_lists_tools(monkeypatch):
    seen: dict[str, object] = {}

    class FakeHttpClient:
        def __init__(self, **kwargs):
            seen["http_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class FakeClient:
        def __init__(self, transport):
            seen["transport"] = transport
            self.protocol_version = "2026-07-28"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def list_tools(self):
            seen["listed"] = True
            return SimpleNamespace(
                tools=[SimpleNamespace(name="files_list"), SimpleNamespace(name="calendar_search")]
            )

    def fake_streamable_http_client(url, *, http_client, terminate_on_close):
        seen["url"] = url
        seen["http_client"] = http_client
        seen["terminate_on_close"] = terminate_on_close
        return object()

    monkeypatch.setattr(native_mcp.httpx2, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(native_mcp, "Client", FakeClient)
    monkeypatch.setattr(native_mcp, "streamable_http_client", fake_streamable_http_client)

    result = await native_mcp.probe_context_agent_mcp(settings())

    kwargs = seen["http_kwargs"]
    assert kwargs["headers"]["Authorization"] == "Bearer test-app-password"
    assert kwargs["follow_redirects"] is False
    assert kwargs["verify"] is True
    assert seen["url"] == (
        "https://cloud.example.com/index.php/apps/app_api/proxy/context_agent/mcp/"
    )
    assert seen["terminate_on_close"] is False
    assert seen["listed"] is True
    assert result.protocol_version == "2026-07-28"
    assert result.tool_names == ("files_list", "calendar_search")
    assert result.tools_truncated is False


async def test_probe_failure_is_sanitized(monkeypatch):
    class FailingHttpClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            raise RuntimeError("Bearer secret-token remote body")

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(native_mcp.httpx2, "AsyncClient", FailingHttpClient)

    with pytest.raises(native_mcp.NativeMCPError) as exc_info:
        await native_mcp.probe_context_agent_mcp(settings())

    assert str(exc_info.value) == "Nextcloud Context Agent MCP probe failed"
    assert "secret-token" not in str(exc_info.value)
