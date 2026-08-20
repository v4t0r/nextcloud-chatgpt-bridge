from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol
from uuid import uuid4

from pydantic import SecretStr

from nextcloud_chatgpt_bridge.connections.models import ConnectionRecord, PendingLoginRecord


class ConnectionStore(Protocol):
    """Tenant-scoped connection metadata store."""

    def put_pending(self, record: PendingLoginRecord) -> None: ...

    def get_pending(self, flow_id: str, tenant_id: str) -> PendingLoginRecord | None: ...

    def delete_pending(self, flow_id: str, tenant_id: str) -> None: ...

    def put_connection(self, record: ConnectionRecord) -> None: ...

    def get_connection(self, connection_id: str, tenant_id: str) -> ConnectionRecord | None: ...

    def list_connections(self, tenant_id: str) -> Iterable[ConnectionRecord]: ...

    def delete_connection(self, connection_id: str, tenant_id: str) -> None: ...


class CredentialStore(Protocol):
    """Tenant-scoped vault boundary. Production implementations must encrypt at rest."""

    def put(self, tenant_id: str, secret: SecretStr) -> str: ...

    def get(self, tenant_id: str, secret_ref: str) -> SecretStr | None: ...

    def delete(self, tenant_id: str, secret_ref: str) -> None: ...


class InMemoryConnectionStore:
    """Development/test store only. Not suitable for public or multi-process deployment."""

    def __init__(self) -> None:
        self._pending: dict[tuple[str, str], PendingLoginRecord] = {}
        self._connections: dict[tuple[str, str], ConnectionRecord] = {}

    def put_pending(self, record: PendingLoginRecord) -> None:
        self._pending[(record.tenant_id, record.flow_id)] = record

    def get_pending(self, flow_id: str, tenant_id: str) -> PendingLoginRecord | None:
        return self._pending.get((tenant_id, flow_id))

    def delete_pending(self, flow_id: str, tenant_id: str) -> None:
        self._pending.pop((tenant_id, flow_id), None)

    def put_connection(self, record: ConnectionRecord) -> None:
        self._connections[(record.tenant_id, record.connection_id)] = record

    def get_connection(self, connection_id: str, tenant_id: str) -> ConnectionRecord | None:
        return self._connections.get((tenant_id, connection_id))

    def list_connections(self, tenant_id: str) -> Iterable[ConnectionRecord]:
        return tuple(
            record
            for (stored_tenant, _connection_id), record in self._connections.items()
            if stored_tenant == tenant_id
        )

    def delete_connection(self, connection_id: str, tenant_id: str) -> None:
        self._connections.pop((tenant_id, connection_id), None)


class InMemoryCredentialStore:
    """Development/test vault. Secrets remain process-memory only and disappear on restart."""

    def __init__(self) -> None:
        self._secrets: dict[tuple[str, str], SecretStr] = {}

    def put(self, tenant_id: str, secret: SecretStr) -> str:
        secret_ref = f"mem:{uuid4().hex}"
        self._secrets[(tenant_id, secret_ref)] = SecretStr(secret.get_secret_value())
        return secret_ref

    def get(self, tenant_id: str, secret_ref: str) -> SecretStr | None:
        secret = self._secrets.get((tenant_id, secret_ref))
        if secret is None:
            return None
        return SecretStr(secret.get_secret_value())

    def delete(self, tenant_id: str, secret_ref: str) -> None:
        self._secrets.pop((tenant_id, secret_ref), None)
