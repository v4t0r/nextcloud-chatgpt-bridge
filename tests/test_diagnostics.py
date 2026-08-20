from __future__ import annotations

from types import SimpleNamespace

import pytest

import nextcloud_chatgpt_bridge.diagnostics as diagnostics
from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.models import FileInfo

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _settings() -> Settings:
    return Settings(
        NEXTCLOUD_BASE_URL="https://cloud.example.com",
        NEXTCLOUD_USERNAME="bridge-user",
        NEXTCLOUD_APP_PASSWORD="test-app-password",  # noqa: S106
        NEXTCLOUD_ROOT_PATH="/ChatGPT",
        NEXTCLOUD_VERIFY_TLS=True,
    )


class FakeOCSClient:
    def __init__(self, settings):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def get_capabilities(self):
        return {
            "version": {"major": 34, "minor": 0, "micro": 1, "string": "34.0.1"},
            "capabilities": {},
        }


class FakeWebDAVClient:
    operations: list[tuple[str, str]] = []

    def __init__(self, settings):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def list_files(self, path=""):
        self.operations.append(("list", path))
        return [FileInfo(path="one.txt", name="one.txt", is_dir=False, size=1)]

    def create_folder(self, path):
        self.operations.append(("mkdir", path))
        return FileInfo(path=path, name=path, is_dir=True, size=0)

    def upload_file(self, path, content, *, overwrite=False):
        self.operations.append(("upload", path))
        assert overwrite is False
        return FileInfo(path=path, name="probe.txt", is_dir=False, size=len(content))

    def download_file(self, path):
        self.operations.append(("download", path))
        return b"nextcloud-chatgpt-bridge smoke test\n"

    def move(self, source, destination, *, overwrite=False):
        self.operations.append(("move", destination))
        assert overwrite is False
        return FileInfo(path=destination, name="probe-renamed.txt", is_dir=False, size=36)

    def stat(self, path):
        self.operations.append(("stat", path))
        return FileInfo(path=path, name="probe-renamed.txt", is_dir=False, size=36)

    def delete(self, path):
        self.operations.append(("delete", path))


async def fake_native_probe(settings):
    return SimpleNamespace(
        protocol_version="2026-07-28",
        tool_names=("files_list",),
    )


async def test_default_diagnostics_are_read_only(monkeypatch):
    FakeWebDAVClient.operations = []
    monkeypatch.setattr(diagnostics, "Settings", _settings)
    monkeypatch.setattr(diagnostics, "OCSClient", FakeOCSClient)
    monkeypatch.setattr(diagnostics, "WebDAVClient", FakeWebDAVClient)
    monkeypatch.setattr(diagnostics, "probe_context_agent_mcp", fake_native_probe)

    result = await diagnostics.run_diagnostics(write_test=False)

    assert result.ocs_ok is True
    assert result.nextcloud_version == "34.0.1"
    assert result.webdav_ok is True
    assert result.root_entries == 1
    assert result.native_mcp_available is True
    assert result.native_mcp_tool_count == 1
    assert result.write_test_requested is False
    assert [operation for operation, _ in FakeWebDAVClient.operations] == ["list"]


async def test_write_smoke_test_is_explicit_and_cleans_up(monkeypatch):
    FakeWebDAVClient.operations = []
    monkeypatch.setattr(diagnostics, "Settings", _settings)
    monkeypatch.setattr(diagnostics, "OCSClient", FakeOCSClient)
    monkeypatch.setattr(diagnostics, "WebDAVClient", FakeWebDAVClient)
    monkeypatch.setattr(diagnostics, "probe_context_agent_mcp", fake_native_probe)

    result = await diagnostics.run_diagnostics(write_test=True)

    operations = [operation for operation, _ in FakeWebDAVClient.operations]
    assert result.write_test_requested is True
    assert result.write_test_ok is True
    assert result.cleanup_ok is True
    assert operations == ["list", "mkdir", "upload", "download", "move", "stat", "delete"]
