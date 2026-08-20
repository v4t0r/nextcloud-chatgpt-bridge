from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol
from uuid import uuid4

from pydantic import SecretStr

from nextcloud_chatgpt_bridge.connections.models import ConnectionRecord, PendingLoginRecord


class ConnectionStore(Protocol):
    """Tenant-scoped connection metadata store."""

    def put_pending(self, record: PendingLoginRecord) -> None: ...

    def get_pending(self, flow_id: str, owner_subject: str) -> PendingLoginRecord | None: ...

    def delete_pending(self, flow_id: str, owner_subject: str) -> None: ...

    def put_connection(self, record: ConnectionRecord) -> None: ...

    def get_connection(self, connection_id: str, owner_subject: str) -> ConnectionRecord | None: ...

    def list_connections(self, owner_subject: str) -> Iterable[ConnectionRecord]: ...

    def delete_connection(self, connection_id: str, owner_subject: str) -> None: ...


class SecretStore(Protocol):
    """Secret-vault boundary. Production implementations must encrypt at rest."""

    def put(self, secret: SecretStr) -> str: ...

    def get(self, secret_ref: str) -> SecretStr | None: ...

    def delete(self, secret_ref: str) -> None: ...


class InMemoryConnectionStore:
    """Development/test store only. Not suitable for public or multi-process deployment."""

    def __init__(self) -> None:
        self._pending: dict[tuple[str, str], PendingLoginRecord] = {}
        self._connections: dict[tuple[str, str], ConnectionRecord] = {}

    def put_pending(self, record: PendingLoginRecord) -> None:
        self._pending[(record.owner_subject, record.flow_id)] = record

    def get_pending(self, flow_id: str, owner_subject: str) -> PendingLoginRecord | None:
        return self._pending.get((owner_subject, flow_id))

    def delete_pending(self, flow_id: str, owner_subject: str) -> None:
        self._pending.pop((owner_subject, flow_id), None)

    def put_connection(self, record: ConnectionRecord) -> None:
        self._connections[(record.owner_subject, record.connection_id)] = record

    def get_connection(self, connection_id: str, owner_subject: str) -> ConnectionRecord | None:
        return self._connections.get((owner_subject, connection_id))

    def list_connections(self, owner_subject: str) -> Iterable[ConnectionRecord]:
        return tuple(
            record
            for (subject, _connection_id), record in self._connections.items()
            if subject == owner_subject
        )

    def delete_connection(self, connection_id: str, owner_subject: str) -> None:
        self._connections.pop((owner_subject, connection_id), None)


class InMemorySecretStore:
    """Development/test vault. Secrets remain process-memory only and disappear on restart."""

    def __init__(self) -> None:
        self._secrets: dict[str, SecretStr] = {}

    def put(self, secret: SecretStr) -> str:
        secret_ref = f"mem:{uuid4().hex}"
        self._secrets[secret_ref] = SecretStr(secret.get_secret_value())
        return secret_ref

    def get(self, secret_ref: str) -> SecretStr | None:
        secret = self._secrets.get(secret_ref)
        if secret is None:
            return None
        return SecretStr(secret.get_secret_value())

    def delete(self, secret_ref: str) -> None:
        self._secrets.pop(secret_ref, None)
