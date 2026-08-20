from __future__ import annotations

from hashlib import sha256

import pytest

from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.household.service import HouseholdNotFoundError, HouseholdService
from nextcloud_chatgpt_bridge.household.store import InMemoryHouseholdProfileStore
from nextcloud_chatgpt_bridge.identity import BridgeIdentity, BridgeSessionContext
from nextcloud_chatgpt_bridge.models import FileInfo

INVOICE = b"""Supplier: Example Energy GmbH
Invoice number: INV-42
Invoice date: 2026-08-01
Grand total: 42,00 EUR
IBAN: DE89 3704 0044 0532 0130 00
"""


def context(subject: str) -> BridgeSessionContext:
    return BridgeSessionContext(
        identity=BridgeIdentity(issuer="https://auth.example.com", subject=subject),
        client_id="chatgpt",
        scopes=frozenset({"nextcloud:use"}),
    )


def settings() -> Settings:
    return Settings(
        NEXTCLOUD_BASE_URL="https://cloud.example.com",
        NEXTCLOUD_USERNAME="bridge-user",
        NEXTCLOUD_APP_PASSWORD="app-password",  # noqa: S106
        NEXTCLOUD_ROOT_PATH="/ChatGPT",
        NEXTCLOUD_MAX_TRANSFER_BYTES=4096,
    )


class FakeSettingsProvider:
    def __init__(self, owner: str) -> None:
        self.owner = owner

    def resolve_settings(self, *, context, connection_id: str):
        if context.tenant_id != self.owner or connection_id != "nc_1234567890123456":
            raise RuntimeError("Connection was not found")
        return settings()


class FakeWebDAV:
    def __init__(self) -> None:
        self.folders: set[str] = set()
        self.files = {
            "Household/Invoices/Inbox/invoice.txt": INVOICE,
            "Household/Invoices/Inbox/ignore.exe": b"ignored",
        }
        self.downloaded: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def ensure_folder(self, path: str):
        self.folders.add(path)
        return FileInfo(path=path, name=path.rsplit("/", 1)[-1], is_dir=True, size=0)

    def list_files(self, path: str):
        result = []
        for file_path, payload in self.files.items():
            if file_path.rsplit("/", 1)[0] == path:
                result.append(
                    FileInfo(
                        path=file_path,
                        name=file_path.rsplit("/", 1)[-1],
                        is_dir=False,
                        size=len(payload),
                        content_type="text/plain",
                    )
                )
        return result

    def stat(self, path: str):
        payload = self.files[path]
        return FileInfo(
            path=path,
            name=path.rsplit("/", 1)[-1],
            is_dir=False,
            size=len(payload),
            content_type="application/json" if path.endswith(".json") else "text/plain",
        )

    def download_file(self, path: str, *, max_bytes: int | None = None):
        self.downloaded.append(path)
        return self.files[path]

    def exists(self, path: str):
        return path in self.files

    def upload_file(self, path: str, content: bytes, *, overwrite: bool = False):
        if path in self.files and not overwrite:
            raise RuntimeError("exists")
        self.files[path] = content
        return self.stat(path)


def make_service(owner: str, webdav: FakeWebDAV) -> HouseholdService:
    return HouseholdService(
        profile_store=InMemoryHouseholdProfileStore(),
        settings_provider=FakeSettingsProvider(owner),
        webdav_factory=lambda _settings: webdav,  # type: ignore[arg-type]
    )


def test_household_profiles_are_tenant_scoped_and_workspace_is_idempotent():
    owner = context("user-a")
    other = context("user-b")
    webdav = FakeWebDAV()
    service = make_service(owner.tenant_id, webdav)

    profile = service.configure_profile(
        context=owner,
        connection_id="nc_1234567890123456",
        display_name="Our Household",
    )
    unchanged = service.configure_profile(
        context=owner,
        connection_id="nc_1234567890123456",
        display_name="Our Household",
    )
    updated = service.configure_profile(
        context=owner,
        connection_id="nc_1234567890123456",
        display_name="Our Household Updated",
    )

    assert unchanged.updated_at == profile.updated_at
    assert updated.profile_id == profile.profile_id
    assert service.list_profiles(context=other) == []
    with pytest.raises(HouseholdNotFoundError):
        service.prepare_workspace(context=other, profile_id=profile.profile_id)

    prepared = service.prepare_workspace(context=owner, profile_id=profile.profile_id)
    assert prepared.ready is True
    assert set(prepared.folders) == webdav.folders


def test_invoice_review_is_inbox_scoped_and_saved_report_is_redacted_and_idempotent():
    owner = context("user-a")
    webdav = FakeWebDAV()
    service = make_service(owner.tenant_id, webdav)
    profile = service.configure_profile(
        context=owner,
        connection_id="nc_1234567890123456",
        display_name="Our Household",
    )

    candidates = service.list_invoice_candidates(context=owner, profile_id=profile.profile_id)
    assert [candidate.name for candidate in candidates] == ["invoice.txt"]

    with pytest.raises(ValueError, match="inbox"):
        service.review_invoice(
            context=owner,
            profile_id=profile.profile_id,
            invoice_path="Other/invoice.txt",
        )
    assert webdav.downloaded == []

    first = service.save_invoice_review(
        context=owner,
        profile_id=profile.profile_id,
        invoice_path="Household/Invoices/Inbox/invoice.txt",
    )
    expected_digest = sha256(INVOICE).hexdigest()
    assert first.saved is True
    assert first.report_path.endswith(f"/{expected_digest}.review.json")
    stored = webdav.files[first.report_path].decode()
    assert "013000" not in stored
    assert "DE89" not in stored
    assert "Example Energy GmbH" in stored

    second = service.save_invoice_review(
        context=owner,
        profile_id=profile.profile_id,
        invoice_path="Household/Invoices/Inbox/invoice.txt",
    )
    assert second.saved is False
    assert second.review.previously_reviewed is True
