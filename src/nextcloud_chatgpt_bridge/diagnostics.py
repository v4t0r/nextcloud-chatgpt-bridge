from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from uuid import uuid4

from nextcloud_chatgpt_bridge.capabilities import build_capability_report
from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.providers.native_mcp import (
    NativeMCPError,
    probe_context_agent_mcp,
)
from nextcloud_chatgpt_bridge.providers.ocs import OCSClient
from nextcloud_chatgpt_bridge.providers.webdav import WebDAVClient


@dataclass(slots=True)
class DiagnosticResult:
    ocs_ok: bool = False
    nextcloud_version: str | None = None
    webdav_ok: bool = False
    root_entries: int | None = None
    native_mcp_available: bool = False
    native_mcp_protocol: str | None = None
    native_mcp_tool_count: int | None = None
    write_test_requested: bool = False
    write_test_ok: bool | None = None
    cleanup_ok: bool | None = None
    failed_stages: list[str] | None = None

    @property
    def successful(self) -> bool:
        if not self.ocs_ok or not self.webdav_ok:
            return False
        if self.write_test_requested and self.write_test_ok is not True:
            return False
        return True


async def run_diagnostics(*, write_test: bool = False) -> DiagnosticResult:
    """Run sanitized live checks. Native MCP discovery never invokes a remote native tool."""
    settings = Settings()
    result = DiagnosticResult(write_test_requested=write_test, failed_stages=[])

    try:
        with OCSClient(settings) as ocs:
            data = ocs.get_capabilities()
        report = build_capability_report(settings, data)
        result.ocs_ok = True
        result.nextcloud_version = report.nextcloud_version
    except Exception:
        result.failed_stages.append("ocs_capabilities")

    try:
        with WebDAVClient(settings) as webdav:
            root_entries = webdav.list_files("")
        result.webdav_ok = True
        result.root_entries = len(root_entries)
    except Exception:
        result.failed_stages.append("webdav_read")

    try:
        native = await probe_context_agent_mcp(settings)
    except NativeMCPError:
        pass
    else:
        result.native_mcp_available = True
        result.native_mcp_protocol = native.protocol_version
        result.native_mcp_tool_count = len(native.tool_names)

    if write_test:
        try:
            await asyncio.to_thread(_run_write_smoke_test, settings, result)
        except Exception:
            result.write_test_ok = False
            result.failed_stages.append("webdav_write")

    return result


def _run_write_smoke_test(settings: Settings, result: DiagnosticResult) -> None:
    """Create, verify, rename and remove one isolated temporary folder below the root."""
    folder = f".bridge-smoke-{uuid4().hex[:12]}"
    original = f"{folder}/probe.txt"
    renamed = f"{folder}/probe-renamed.txt"
    payload = b"nextcloud-chatgpt-bridge smoke test\n"
    created = False

    try:
        with WebDAVClient(settings) as webdav:
            webdav.create_folder(folder)
            created = True
            webdav.upload_file(original, payload, overwrite=False)
            downloaded = webdav.download_file(original)
            if downloaded != payload:
                raise RuntimeError("Smoke-test download did not match uploaded content")
            webdav.move(original, renamed, overwrite=False)
            moved = webdav.stat(renamed)
            if moved.is_dir:
                raise RuntimeError("Smoke-test moved file was reported as a directory")
            webdav.delete(folder)
            created = False
        result.write_test_ok = True
        result.cleanup_ok = True
    finally:
        if created:
            try:
                with WebDAVClient(settings) as cleanup_client:
                    cleanup_client.delete(folder)
                result.cleanup_ok = True
            except Exception:
                result.cleanup_ok = False
        if result.write_test_ok is None:
            result.write_test_ok = False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run sanitized connectivity checks against the configured Nextcloud instance."
    )
    parser.add_argument(
        "--write-test",
        action="store_true",
        help=(
            "Also create/upload/read/move/delete one temporary folder below NEXTCLOUD_ROOT_PATH. "
            "Without this flag diagnostics are read-only."
        ),
    )
    args = parser.parse_args()

    result = asyncio.run(run_diagnostics(write_test=args.write_test))
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    raise SystemExit(0 if result.successful else 1)


if __name__ == "__main__":
    main()
