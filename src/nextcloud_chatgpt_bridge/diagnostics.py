from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from uuid import uuid4

from nextcloud_chatgpt_bridge import __version__
from nextcloud_chatgpt_bridge.app_access import build_app_access_report
from nextcloud_chatgpt_bridge.capabilities import build_capability_report
from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.household.models import InvoiceReviewStatus
from nextcloud_chatgpt_bridge.household.service import HouseholdService
from nextcloud_chatgpt_bridge.household.store import InMemoryHouseholdProfileStore
from nextcloud_chatgpt_bridge.identity import BridgeIdentity, BridgeSessionContext
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
    v020_test_requested: bool = False
    app_access_ok: bool | None = None
    visible_app_count: int | None = None
    search_provider_count: int | None = None
    shares_ok: bool | None = None
    root_share_count: int | None = None
    household_test_ok: bool | None = None
    household_cleanup_ok: bool | None = None
    failed_stages: list[str] | None = None

    @property
    def successful(self) -> bool:
        if not self.ocs_ok or not self.webdav_ok:
            return False
        if self.write_test_requested and self.write_test_ok is not True:
            return False
        if self.v020_test_requested and not all(
            value is True
            for value in (
                self.app_access_ok,
                self.shares_ok,
                self.household_test_ok,
                self.household_cleanup_ok,
            )
        ):
            return False
        return True


async def run_diagnostics(
    *,
    write_test: bool = False,
    v020_test: bool = False,
) -> DiagnosticResult:
    """Run sanitized live checks. Native MCP discovery never invokes a remote native tool."""
    settings = Settings()
    result = DiagnosticResult(
        write_test_requested=write_test,
        v020_test_requested=v020_test,
        failed_stages=[],
    )

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

    if v020_test:
        try:
            with OCSClient(settings) as ocs:
                capability_data = ocs.get_capabilities()
                navigation_apps = ocs.get_navigation_apps()
                search_providers = ocs.get_search_providers()
            app_report = build_app_access_report(
                settings,
                capability_data,
                navigation_apps=navigation_apps,
                search_providers=search_providers,
            )
            result.app_access_ok = True
            result.visible_app_count = len(app_report.apps)
            result.search_provider_count = len(app_report.search_providers)
        except Exception:
            result.app_access_ok = False
            result.failed_stages.append("app_access")

        try:
            root = settings.nextcloud_root_path.rstrip("/")
            with OCSClient(settings) as ocs:
                shares = ocs.list_shares(path=root, include_subfiles=True)
            if any(
                share.path is not None
                and share.path != root
                and not share.path.startswith(f"{root}/")
                for share in shares
            ):
                raise RuntimeError("Share inventory escaped the configured root")
            result.shares_ok = True
            result.root_share_count = len(shares)
        except Exception:
            result.shares_ok = False
            result.failed_stages.append("root_shares")

        try:
            await asyncio.to_thread(_run_v020_smoke_test, settings, result)
        except Exception:
            result.household_test_ok = False
            result.failed_stages.append("household_invoice")
        finally:
            if (
                result.household_cleanup_ok is not True
                and "household_cleanup" not in result.failed_stages
            ):
                result.failed_stages.append("household_cleanup")

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


class _StaticSettingsProvider:
    def __init__(self, settings: Settings, *, tenant_id: str, connection_id: str) -> None:
        self.settings = settings
        self.tenant_id = tenant_id
        self.connection_id = connection_id

    def resolve_settings(
        self,
        *,
        context: BridgeSessionContext,
        connection_id: str,
    ) -> Settings:
        if context.tenant_id != self.tenant_id or connection_id != self.connection_id:
            raise RuntimeError("Diagnostic connection was not found")
        return self.settings


def _run_v020_smoke_test(settings: Settings, result: DiagnosticResult) -> None:
    """Exercise the tenant-bound household flow with synthetic data and guaranteed cleanup."""
    folder = f".bridge-v020-smoke-{uuid4().hex[:12]}"
    connection_id = f"nc_{uuid4().hex}"
    context = BridgeSessionContext(
        identity=BridgeIdentity(
            issuer="urn:nextcloud-chatgpt-bridge:diagnostic",
            subject=uuid4().hex,
        ),
        client_id="release-diagnostic",
        scopes=frozenset({"nextcloud:use"}),
    )
    inbox = f"{folder}/Invoices/Inbox"
    archive = f"{folder}/Invoices/Archive"
    reports = f"{folder}/Invoices/Reviews"
    invoice_path = f"{inbox}/synthetic-invoice.txt"
    payload = b"""Supplier: Synthetic Energy GmbH
Invoice number: SYNTHETIC-2026-0042
Invoice date: 2026-08-01
Due date: 2026-08-15
Net amount: 100,00 EUR
VAT: 19,00 EUR
Grand total: 119,00 EUR
Payment reference: SYNTHETIC-0042
IBAN: DE89 3704 0044 0532 0130 00
"""
    service = HouseholdService(
        profile_store=InMemoryHouseholdProfileStore(),
        settings_provider=_StaticSettingsProvider(
            settings,
            tenant_id=context.tenant_id,
            connection_id=connection_id,
        ),
        webdav_factory=WebDAVClient,
    )
    cleanup_required = False

    try:
        profile = service.configure_profile(
            context=context,
            connection_id=connection_id,
            display_name="Synthetic diagnostic household",
            invoice_inbox_path=inbox,
            invoice_archive_path=archive,
            review_report_path=reports,
        )
        cleanup_required = True
        service.prepare_workspace(context=context, profile_id=profile.profile_id)
        with WebDAVClient(settings) as webdav:
            webdav.upload_file(invoice_path, payload, overwrite=False)

        candidates = service.list_invoice_candidates(
            context=context,
            profile_id=profile.profile_id,
        )
        if [candidate.path for candidate in candidates] != [invoice_path]:
            raise RuntimeError("Synthetic invoice was not isolated in the household inbox")

        saved = service.save_invoice_review(
            context=context,
            profile_id=profile.profile_id,
            invoice_path=invoice_path,
        )
        duplicate = service.save_invoice_review(
            context=context,
            profile_id=profile.profile_id,
            invoice_path=invoice_path,
        )
        with WebDAVClient(settings) as webdav:
            report_payload = webdav.download_file(saved.report_path)
        if not saved.saved or duplicate.saved or not duplicate.review.previously_reviewed:
            raise RuntimeError("Immutable duplicate review behavior failed")
        if saved.review.status != InvoiceReviewStatus.READY_FOR_HUMAN_REVIEW:
            raise RuntimeError("Synthetic invoice did not reach human-review readiness")
        if saved.review.invoice_number != "SYNTHETIC-2026-0042":
            raise RuntimeError("Synthetic invoice number was not extracted")
        if b"DE89" in report_payload or b"0130 00" in report_payload:
            raise RuntimeError("Review report contained an unredacted IBAN")
        if b"did not approve" not in report_payload:
            raise RuntimeError("Review report omitted the human decision boundary")
        result.household_test_ok = True
    finally:
        if cleanup_required:
            try:
                with WebDAVClient(settings) as cleanup_client:
                    if cleanup_client.exists(folder):
                        cleanup_client.delete(folder)
                result.household_cleanup_ok = True
            except Exception:
                result.household_cleanup_ok = False
        if result.household_test_ok is None:
            result.household_test_ok = False
        if result.household_cleanup_ok is None:
            result.household_cleanup_ok = not cleanup_required


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run sanitized connectivity checks against the configured Nextcloud instance."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--write-test",
        action="store_true",
        help=(
            "Also create/upload/read/move/delete one temporary folder below NEXTCLOUD_ROOT_PATH. "
            "Without this flag diagnostics are read-only."
        ),
    )
    parser.add_argument(
        "--v020-test",
        action="store_true",
        help=(
            "Also inspect user-visible apps/root shares and run one isolated synthetic household "
            "invoice review below NEXTCLOUD_ROOT_PATH, including immutable report and cleanup checks."
        ),
    )
    args = parser.parse_args()

    result = asyncio.run(
        run_diagnostics(
            write_test=args.write_test,
            v020_test=args.v020_test,
        )
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    raise SystemExit(0 if result.successful else 1)


if __name__ == "__main__":
    main()
