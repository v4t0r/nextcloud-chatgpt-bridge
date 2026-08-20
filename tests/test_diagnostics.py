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

    def get_navigation_apps(self):
        return [SimpleNamespace(app_id="files", display_name="Files")]

    def get_search_providers(self):
        return [SimpleNamespace(provider_id="files", display_name="Files")]

    def list_shares(self, *, path, include_subfiles=False):
        assert path == "/ChatGPT"
        assert include_subfiles is True
        return [SimpleNamespace(path="/ChatGPT/Documents/shared.txt")]


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


class FakeV020WebDAVClient:
    folders: set[str] = {""}
    files: dict[str, bytes] = {}

    def __init__(self, settings):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def ensure_folder(self, path):
        parts = path.split("/")
        for index in range(1, len(parts) + 1):
            self.folders.add("/".join(parts[:index]))
        return FileInfo(path=path, name=parts[-1], is_dir=True, size=0)

    def upload_file(self, path, content, *, overwrite=False):
        if path in self.files and not overwrite:
            raise RuntimeError("exists")
        self.files[path] = content
        return self.stat(path)

    def list_files(self, path=""):
        return [
            self.stat(file_path)
            for file_path in self.files
            if file_path.rsplit("/", 1)[0] == path
        ]

    def stat(self, path):
        content = self.files[path]
        return FileInfo(
            path=path,
            name=path.rsplit("/", 1)[-1],
            is_dir=False,
            size=len(content),
            content_type="application/json" if path.endswith(".json") else "text/plain",
        )

    def download_file(self, path, *, max_bytes=None):
        content = self.files[path]
        assert max_bytes is None or len(content) <= max_bytes
        return content

    def exists(self, path):
        return path in self.folders or path in self.files

    def delete(self, path):
        prefix = f"{path}/"
        type(self).files = {
            item_path: content
            for item_path, content in self.files.items()
            if item_path != path and not item_path.startswith(prefix)
        }
        type(self).folders = {
            folder
            for folder in self.folders
            if folder != path and not folder.startswith(prefix)
        }


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


async def test_v020_diagnostics_require_app_share_and_household_checks(monkeypatch):
    def fake_household_test(settings, result):
        result.household_test_ok = True
        result.household_cleanup_ok = True

    monkeypatch.setattr(diagnostics, "Settings", _settings)
    monkeypatch.setattr(diagnostics, "OCSClient", FakeOCSClient)
    monkeypatch.setattr(diagnostics, "WebDAVClient", FakeWebDAVClient)
    monkeypatch.setattr(diagnostics, "probe_context_agent_mcp", fake_native_probe)
    monkeypatch.setattr(diagnostics, "_run_v020_smoke_test", fake_household_test)

    result = await diagnostics.run_diagnostics(v020_test=True)

    assert result.successful is True
    assert result.v020_test_requested is True
    assert result.app_access_ok is True
    assert result.visible_app_count == 1
    assert result.search_provider_count == 1
    assert result.shares_ok is True
    assert result.root_share_count == 1
    assert result.household_test_ok is True
    assert result.household_cleanup_ok is True


async def test_v020_cleanup_failure_fails_the_diagnostic(monkeypatch):
    def fake_household_test(settings, result):
        result.household_test_ok = True
        result.household_cleanup_ok = False

    monkeypatch.setattr(diagnostics, "Settings", _settings)
    monkeypatch.setattr(diagnostics, "OCSClient", FakeOCSClient)
    monkeypatch.setattr(diagnostics, "WebDAVClient", FakeWebDAVClient)
    monkeypatch.setattr(diagnostics, "probe_context_agent_mcp", fake_native_probe)
    monkeypatch.setattr(diagnostics, "_run_v020_smoke_test", fake_household_test)

    result = await diagnostics.run_diagnostics(v020_test=True)

    assert result.successful is False
    assert "household_cleanup" in result.failed_stages


def test_v020_household_smoke_uses_synthetic_data_and_cleans_up(monkeypatch):
    FakeV020WebDAVClient.folders = {""}
    FakeV020WebDAVClient.files = {}
    monkeypatch.setattr(diagnostics, "WebDAVClient", FakeV020WebDAVClient)
    result = diagnostics.DiagnosticResult(failed_stages=[])

    diagnostics._run_v020_smoke_test(_settings(), result)

    assert result.household_test_ok is True
    assert result.household_cleanup_ok is True
    assert FakeV020WebDAVClient.folders == {""}
    assert FakeV020WebDAVClient.files == {}
