from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from nextcloud_chatgpt_bridge.household.models import HouseholdProfileRecord


class HouseholdProfileStore(Protocol):
    """Tenant-scoped non-secret household configuration store."""

    def put_profile(self, record: HouseholdProfileRecord) -> None: ...

    def get_profile(self, profile_id: str, tenant_id: str) -> HouseholdProfileRecord | None: ...

    def get_profile_for_connection(
        self,
        connection_id: str,
        tenant_id: str,
    ) -> HouseholdProfileRecord | None: ...

    def list_profiles(self, tenant_id: str) -> Iterable[HouseholdProfileRecord]: ...

    def delete_profile(self, profile_id: str, tenant_id: str) -> None: ...


class InMemoryHouseholdProfileStore:
    """Development/test store; hosted deployments must use durable tenant-scoped storage."""

    def __init__(self) -> None:
        self._profiles: dict[tuple[str, str], HouseholdProfileRecord] = {}

    def put_profile(self, record: HouseholdProfileRecord) -> None:
        existing = self.get_profile_for_connection(record.connection_id, record.tenant_id)
        if existing is not None and existing.profile_id != record.profile_id:
            raise ValueError("A household profile already exists for this connection")
        self._profiles[(record.tenant_id, record.profile_id)] = record

    def get_profile(self, profile_id: str, tenant_id: str) -> HouseholdProfileRecord | None:
        return self._profiles.get((tenant_id, profile_id))

    def get_profile_for_connection(
        self,
        connection_id: str,
        tenant_id: str,
    ) -> HouseholdProfileRecord | None:
        return next(
            (
                record
                for (stored_tenant, _profile_id), record in self._profiles.items()
                if stored_tenant == tenant_id and record.connection_id == connection_id
            ),
            None,
        )

    def list_profiles(self, tenant_id: str) -> Iterable[HouseholdProfileRecord]:
        return tuple(
            sorted(
                (
                    record
                    for (stored_tenant, _profile_id), record in self._profiles.items()
                    if stored_tenant == tenant_id
                ),
                key=lambda record: (record.created_at, record.profile_id),
            )
        )

    def delete_profile(self, profile_id: str, tenant_id: str) -> None:
        self._profiles.pop((tenant_id, profile_id), None)
