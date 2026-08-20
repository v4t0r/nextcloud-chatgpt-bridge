from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp import Client

import nextcloud_chatgpt_bridge.server as server
from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.models import FileInfo

pytestmark = pytest.mark.anyio


class FakeWebDAVClient:
    def __init__(self) -> None:
        self.download_called = False
        self.uploads: list[tuple[str, bytes, bool]] = []
        self.deleted: list[str] = []

    def __enter__(self) -> FakeWebDAVClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def list_files(self, path: str = "") -> list[FileInfo]:
        return [
            FileInfo(
                path="notes.txt",
                name="notes.txt",
                is_dir=False,
                size=5,
                content_type="text/plain",
            )
        ]

    def stat(self, path: str) -> FileInfo:
        if path == "huge.bin":
            return FileInfo(path=path, name=path, is_dir=False, size=10_000)
        return FileInfo(
            path=path,
            name=path.rsplit("/", 1)[-1],
            is_dir=False,
            size=5,
            content_type="text/plain",
        )

    def download_file(self, path: str) -> bytes:
        self.download_called = True
        return b"hello"

    def upload_file(self, path: str, content: bytes, *, overwrite: bool = False) -> FileInfo:
        self.uploads.append((path, content, overwrite))
        return FileInfo(
            path=path,
            name=path.rsplit("/", 1)[-1],
            is_dir=False,
            size=len(content),
            content_type="application/octet-stream",
        )

    def create_folder(self, path: str) -> FileInfo:
        return FileInfo(path=path, name=path.rsplit("/", 1)[-1], is_dir=True, size=0)

    def move(self, source: str, destination: str, *, overwrite: bool = False) -> FileInfo:
        return FileInfo(
            path=destination,
            name=destination.rsplit("/", 1)[-1],
            is_dir=False,
            size=5,
        )

    def delete(self, path: str) -> None:
        if path in {"", "/"}:
            raise ValueError("Refusing to delete the configured Nextcloud root")
        self.deleted.append(path)


def _settings() -> Settings:
    return Settings(
        NEXTCLOUD_BASE_URL="https://cloud.example.com",
        NEXTCLOUD_USERNAME="bridge-user",
        NEXTCLOUD_APP_PASSWORD="test-app-password",  # noqa: S106
        NEXTCLOUD_ROOT_PATH="/ChatGPT",
        NEXTCLOUD_VERIFY_TLS=True,
        NEXTCLOUD_MAX_TRANSFER_BYTES=1024,
    )


def install_fake(monkeypatch) -> FakeWebDAVClient:
    fake = FakeWebDAVClient()
    monkeypatch.setattr(server, "_new_client", lambda: fake)
    monkeypatch.setattr(server, "_safe_settings", _settings)
    return fake


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_mcp_lists_file_and_discovery_tools_with_risk_annotations(monkeypatch):
    install_fake(monkeypatch)

    async with Client(server.mcp) as client:
        listed = await client.list_tools()

    tools = {tool.name: tool for tool in listed.tools}
    assert {
        "get_nextcloud_capabilities",
        "probe_native_nextcloud_mcp",
        "list_files",
        "get_file_info",
        "read_text_file",
        "download_file_base64",
        "write_text_file",
        "upload_file_base64",
        "create_folder",
        "move_file",
        "delete_file",
    } <= tools.keys()
    assert tools["get_nextcloud_capabilities"].annotations.read_only_hint is True
    assert tools["probe_native_nextcloud_mcp"].annotations.read_only_hint is True
    assert tools["list_files"].annotations.read_only_hint is True
    assert tools["delete_file"].annotations.destructive_hint is True
    assert tools["create_folder"].annotations.destructive_hint is False


async def test_native_mcp_probe_returns_available_without_invoking_tools(monkeypatch):
    install_fake(monkeypatch)

    async def fake_probe(settings):
        return SimpleNamespace(
            endpoint="https://cloud.example.com/index.php/apps/app_api/proxy/context_agent/mcp/",
            protocol_version="2026-07-28",
            tool_names=("files_list", "calendar_search"),
            tools_truncated=False,
        )

    monkeypatch.setattr(server, "probe_context_agent_mcp", fake_probe)

    async with Client(server.mcp) as client:
        result = await client.call_tool("probe_native_nextcloud_mcp", {})

    assert result.is_error is False
    assert result.structured_content["available"] is True
    assert result.structured_content["protocol_version"] == "2026-07-28"
    assert result.structured_content["tool_names"] == ["files_list", "calendar_search"]


async def test_native_mcp_probe_reports_unavailable_without_leaking_failure(monkeypatch):
    install_fake(monkeypatch)

    async def failing_probe(settings):
        raise server.NativeMCPError("internal sensitive detail")

    monkeypatch.setattr(server, "probe_context_agent_mcp", failing_probe)

    async with Client(server.mcp) as client:
        result = await client.call_tool("probe_native_nextcloud_mcp", {})

    assert result.is_error is False
    assert result.structured_content["available"] is False
    assert result.structured_content["tool_names"] == []
    assert "internal sensitive detail" not in str(result.structured_content)


async def test_mcp_reads_utf8_text_as_structured_output(monkeypatch):
    fake = install_fake(monkeypatch)

    async with Client(server.mcp) as client:
        result = await client.call_tool("read_text_file", {"path": "notes.txt"})

    assert result.is_error is False
    assert result.structured_content["path"] == "notes.txt"
    assert result.structured_content["content"] == "hello"
    assert result.structured_content["size"] == 5
    assert fake.download_called is True


async def test_mcp_blocks_oversized_download_before_get(monkeypatch):
    fake = install_fake(monkeypatch)

    async with Client(server.mcp) as client:
        result = await client.call_tool("download_file_base64", {"path": "huge.bin"})

    assert result.is_error is True
    assert fake.download_called is False
    assert "transfer limit" in result.content[0].text.lower()


async def test_mcp_write_defaults_to_no_overwrite(monkeypatch):
    fake = install_fake(monkeypatch)

    async with Client(server.mcp) as client:
        result = await client.call_tool(
            "write_text_file",
            {"path": "report.txt", "content": "hello"},
        )

    assert result.is_error is False
    assert fake.uploads == [("report.txt", b"hello", False)]


async def test_mcp_delete_root_is_a_tool_error(monkeypatch):
    install_fake(monkeypatch)

    async with Client(server.mcp) as client:
        result = await client.call_tool("delete_file", {"path": ""})

    assert result.is_error is True
    assert "refusing to delete" in result.content[0].text.lower()
