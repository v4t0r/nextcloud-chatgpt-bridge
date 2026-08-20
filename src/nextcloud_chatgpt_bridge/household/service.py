from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import PurePosixPath
from secrets import token_urlsafe
from typing import Protocol

from nextcloud_chatgpt_bridge.config import Settings, normalize_relative_path
from nextcloud_chatgpt_bridge.household.invoices import InvoiceReviewer
from nextcloud_chatgpt_bridge.household.models import (
    HouseholdProfileRecord,
    HouseholdProfileSummary,
    HouseholdWorkspaceResult,
    InvoiceCandidate,
    InvoiceCheck,
    InvoiceCheckOutcome,
    InvoiceReview,
    InvoiceReviewStatus,
    SavedInvoiceReview,
)
from nextcloud_chatgpt_bridge.household.store import HouseholdProfileStore
from nextcloud_chatgpt_bridge.identity import BridgeSessionContext
from nextcloud_chatgpt_bridge.providers.webdav import WebDAVClient

_CURRENCY = re.compile(r"^[A-Z]{3}$")
_INVOICE_SUFFIXES = {".pdf", ".txt", ".md", ".csv", ".json", ".xml", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
_OCR_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


class HouseholdError(RuntimeError):
    pass


class HouseholdNotFoundError(HouseholdError):
    pass


class ConnectionSettingsProvider(Protocol):
    def resolve_settings(
        self,
        *,
        context: BridgeSessionContext,
        connection_id: str,
    ) -> Settings: ...


class HouseholdService:
    """Tenant-bound household configuration and invoice workflows."""

    def __init__(
        self,
        *,
        profile_store: HouseholdProfileStore,
        settings_provider: ConnectionSettingsProvider,
        reviewer: InvoiceReviewer | None = None,
        webdav_factory: Callable[[Settings], WebDAVClient] = WebDAVClient,
    ) -> None:
        self.profile_store = profile_store
        self.settings_provider = settings_provider
        self.reviewer = reviewer or InvoiceReviewer()
        self.webdav_factory = webdav_factory

    def configure_profile(
        self,
        *,
        context: BridgeSessionContext,
        connection_id: str,
        display_name: str,
        invoice_inbox_path: str = "Household/Invoices/Inbox",
        invoice_archive_path: str = "Household/Invoices/Archive",
        review_report_path: str = "Household/Invoices/Reviews",
        default_currency: str = "EUR",
    ) -> HouseholdProfileSummary:
        self.settings_provider.resolve_settings(context=context, connection_id=connection_id)
        name = " ".join(display_name.split())
        if not name or len(name) > 128:
            raise ValueError("Household display name must contain between 1 and 128 characters")
        currency = default_currency.strip().upper()
        if not _CURRENCY.fullmatch(currency):
            raise ValueError("Household currency must be a three-letter ISO currency code")
        inbox = normalize_relative_path(invoice_inbox_path, field_name="Invoice inbox path")
        archive = normalize_relative_path(invoice_archive_path, field_name="Invoice archive path")
        reports = normalize_relative_path(review_report_path, field_name="Review report path")
        if len({inbox, archive, reports}) != 3:
            raise ValueError("Household invoice folders must be distinct")

        existing = self.profile_store.get_profile_for_connection(connection_id, context.tenant_id)
        if existing is not None and (
            existing.display_name,
            existing.invoice_inbox_path,
            existing.invoice_archive_path,
            existing.review_report_path,
            existing.default_currency,
        ) == (name, inbox, archive, reports, currency):
            return self._summary(existing)

        now = datetime.now(UTC)
        record = HouseholdProfileRecord(
            profile_id=existing.profile_id if existing else f"hh_{token_urlsafe(32)}",
            tenant_id=context.tenant_id,
            connection_id=connection_id,
            display_name=name,
            invoice_inbox_path=inbox,
            invoice_archive_path=archive,
            review_report_path=reports,
            default_currency=currency,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self.profile_store.put_profile(record)
        return self._summary(record)

    def list_profiles(self, *, context: BridgeSessionContext) -> list[HouseholdProfileSummary]:
        return [self._summary(record) for record in self.profile_store.list_profiles(context.tenant_id)]

    def prepare_workspace(
        self,
        *,
        context: BridgeSessionContext,
        profile_id: str,
    ) -> HouseholdWorkspaceResult:
        profile = self._owned_profile(context, profile_id)
        settings = self.settings_provider.resolve_settings(
            context=context,
            connection_id=profile.connection_id,
        )
        folders = [
            profile.invoice_inbox_path,
            profile.invoice_archive_path,
            profile.review_report_path,
        ]
        with self.webdav_factory(settings) as client:
            for folder in folders:
                client.ensure_folder(folder)
        return HouseholdWorkspaceResult(profile_id=profile.profile_id, folders=folders)

    def list_invoice_candidates(
        self,
        *,
        context: BridgeSessionContext,
        profile_id: str,
    ) -> list[InvoiceCandidate]:
        profile, settings = self._profile_and_settings(context, profile_id)
        with self.webdav_factory(settings) as client:
            entries = client.list_files(profile.invoice_inbox_path)
        result: list[InvoiceCandidate] = []
        for item in sorted(entries, key=lambda value: value.name.casefold()):
            suffix = PurePosixPath(item.name).suffix.lower()
            if (
                item.is_dir
                or suffix not in _INVOICE_SUFFIXES
                or item.size is None
                or item.size > settings.max_transfer_bytes
            ):
                continue
            result.append(
                InvoiceCandidate(
                    path=item.path,
                    name=item.name,
                    size=item.size,
                    content_type=item.content_type,
                    last_modified=item.last_modified,
                    requires_ocr=suffix in _OCR_SUFFIXES,
                )
            )
            if len(result) >= 100:
                break
        return result

    def review_invoice(
        self,
        *,
        context: BridgeSessionContext,
        profile_id: str,
        invoice_path: str,
    ) -> InvoiceReview:
        profile, settings = self._profile_and_settings(context, profile_id)
        path = self._invoice_path(profile, invoice_path)
        with self.webdav_factory(settings) as client:
            info = client.stat(path)
            if info.is_dir or info.size is None:
                raise ValueError("Invoice path must reference a bounded file")
            if info.size > settings.max_transfer_bytes:
                raise ValueError("Invoice exceeds the configured transfer limit")
            payload = client.download_file(path, max_bytes=settings.max_transfer_bytes)
            review = self.reviewer.review(
                payload,
                path=path,
                content_type=info.content_type,
                expected_currency=profile.default_currency,
            )
            report_path = self._report_path(profile, review.file_sha256)
            previously_reviewed = client.exists(report_path)
        if previously_reviewed:
            review = review.model_copy(
                update={
                    "previously_reviewed": True,
                    "status": InvoiceReviewStatus.MANUAL_REVIEW_REQUIRED,
                    "checks": [
                        *review.checks,
                        InvoiceCheck(
                            code="duplicate_file_hash",
                            outcome=InvoiceCheckOutcome.WARNING,
                            message="An immutable review report already exists for this file hash",
                        ),
                    ],
                }
            )
        return review

    def save_invoice_review(
        self,
        *,
        context: BridgeSessionContext,
        profile_id: str,
        invoice_path: str,
    ) -> SavedInvoiceReview:
        profile, settings = self._profile_and_settings(context, profile_id)
        review = self.review_invoice(
            context=context,
            profile_id=profile_id,
            invoice_path=invoice_path,
        )
        report_path = self._report_path(profile, review.file_sha256)
        if review.previously_reviewed:
            return SavedInvoiceReview(
                profile_id=profile.profile_id,
                report_path=report_path,
                saved=False,
                review=review,
            )
        payload = json.dumps(
            review.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ).encode("utf-8")
        with self.webdav_factory(settings) as client:
            client.ensure_folder(profile.review_report_path)
            client.upload_file(report_path, payload, overwrite=False)
        return SavedInvoiceReview(
            profile_id=profile.profile_id,
            report_path=report_path,
            saved=True,
            review=review,
        )

    def _profile_and_settings(
        self,
        context: BridgeSessionContext,
        profile_id: str,
    ) -> tuple[HouseholdProfileRecord, Settings]:
        profile = self._owned_profile(context, profile_id)
        settings = self.settings_provider.resolve_settings(
            context=context,
            connection_id=profile.connection_id,
        )
        return profile, settings

    def _owned_profile(
        self,
        context: BridgeSessionContext,
        profile_id: str,
    ) -> HouseholdProfileRecord:
        profile = self.profile_store.get_profile(profile_id, context.tenant_id)
        if profile is None:
            raise HouseholdNotFoundError("Household profile was not found")
        return profile

    @staticmethod
    def _invoice_path(profile: HouseholdProfileRecord, invoice_path: str) -> str:
        normalized = normalize_relative_path(invoice_path, field_name="Invoice path")
        candidate = PurePosixPath(normalized)
        inbox = PurePosixPath(profile.invoice_inbox_path)
        if not candidate.is_relative_to(inbox):
            raise ValueError("Invoice path must stay inside the household invoice inbox")
        return str(candidate)

    @staticmethod
    def _report_path(profile: HouseholdProfileRecord, file_sha256: str) -> str:
        return f"{profile.review_report_path}/{file_sha256}.review.json"

    @staticmethod
    def _summary(record: HouseholdProfileRecord) -> HouseholdProfileSummary:
        return HouseholdProfileSummary(
            profile_id=record.profile_id,
            connection_id=record.connection_id,
            display_name=record.display_name,
            invoice_inbox_path=record.invoice_inbox_path,
            invoice_archive_path=record.invoice_archive_path,
            review_report_path=record.review_report_path,
            default_currency=record.default_currency,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
