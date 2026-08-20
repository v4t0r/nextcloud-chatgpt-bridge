from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe

from nextcloud_chatgpt_bridge.config import Settings, normalize_root_path
from nextcloud_chatgpt_bridge.connections.login_flow import LoginFlowClient, LoginFlowError
from nextcloud_chatgpt_bridge.connections.models import (
    ConnectStart,
    ConnectionRecord,
    ConnectionSummary,
    DisconnectResult,
    PendingLoginRecord,
)
from nextcloud_chatgpt_bridge.connections.store import ConnectionStore, SecretStore
from nextcloud_chatgpt_bridge.providers.ocs import OCSClient, OCSError


class ConnectionError(RuntimeError):
    pass


class ConnectionNotFoundError(ConnectionError):
    pass


class ConnectionExpiredError(ConnectionError):
    pass


class ConnectionService:
    """Owns Nextcloud account linking without ever exposing long-lived credentials to MCP/UI."""

    def __init__(
        self,
        *,
        connection_store: ConnectionStore,
        secret_store: SecretStore,
        login_client: LoginFlowClient,
    ) -> None:
        self.connection_store = connection_store
        self.secret_store = secret_store
        self.login_client = login_client

    @staticmethod
    def _require_subject(owner_subject: str) -> str:
        subject = owner_subject.strip()
        if not subject:
            raise ConnectionError("Authenticated user identity is required")
        return subject

    def begin_connection(
        self,
        *,
        owner_subject: str,
        base_url: str,
        root_path: str = "/ChatGPT",
    ) -> ConnectStart:
        subject = self._require_subject(owner_subject)
        root = normalize_root_path(root_path)
        challenge = self.login_client.initiate(base_url)
        flow_id = f"flow_{token_urlsafe(32)}"
        self.connection_store.put_pending(
            PendingLoginRecord(
                flow_id=flow_id,
                owner_subject=subject,
                root_path=root,
                challenge=challenge,
            )
        )
        return ConnectStart(
            flow_id=flow_id,
            login_url=challenge.login_url,
            expires_at=challenge.expires_at,
        )

    def poll_connection(
        self,
        *,
        owner_subject: str,
        flow_id: str,
    ) -> ConnectionSummary | None:
        subject = self._require_subject(owner_subject)
        pending = self.connection_store.get_pending(flow_id)
        if pending is None or pending.owner_subject != subject:
            raise ConnectionNotFoundError("Connection flow was not found")
        if datetime.now(UTC) >= pending.challenge.expires_at:
            self.connection_store.delete_pending(flow_id)
            raise ConnectionExpiredError("Connection flow has expired")

        try:
            credentials = self.login_client.poll(pending.challenge)
        except LoginFlowError as exc:
            raise ConnectionError("Nextcloud account linking failed") from exc
        if credentials is None:
            return None

        credential_ref = self.secret_store.put(credentials.app_password)
        connection_id = f"nc_{token_urlsafe(32)}"
        record = ConnectionRecord(
            connection_id=connection_id,
            owner_subject=subject,
            base_url=credentials.server,
            login_name=credentials.login_name,
            root_path=pending.root_path,
            credential_ref=credential_ref,
            verify_tls=True,
        )

        try:
            self.connection_store.put_connection(record)
        except Exception:
            self.secret_store.delete(credential_ref)
            raise
        finally:
            self.connection_store.delete_pending(flow_id)

        return self._summary(record)

    def list_connections(self, *, owner_subject: str) -> list[ConnectionSummary]:
        subject = self._require_subject(owner_subject)
        return [
            self._summary(record)
            for record in self.connection_store.list_connections()
            if record.owner_subject == subject
        ]

    def update_root_path(
        self,
        *,
        owner_subject: str,
        connection_id: str,
        root_path: str,
    ) -> ConnectionSummary:
        record = self._get_owned_record(owner_subject, connection_id)
        updated = record.model_copy(update={"root_path": normalize_root_path(root_path)})
        self.connection_store.put_connection(updated)
        return self._summary(updated)

    def resolve_settings(self, *, owner_subject: str, connection_id: str) -> Settings:
        record = self._get_owned_record(owner_subject, connection_id)
        secret = self.secret_store.get(record.credential_ref)
        if secret is None:
            raise ConnectionError("Connection credential is unavailable")

        return Settings(
            NEXTCLOUD_BASE_URL=str(record.base_url),
            NEXTCLOUD_USERNAME=record.login_name,
            NEXTCLOUD_APP_PASSWORD=secret.get_secret_value(),
            NEXTCLOUD_ROOT_PATH=record.root_path,
            NEXTCLOUD_VERIFY_TLS=record.verify_tls,
            NEXTCLOUD_ALLOW_INSECURE_HTTP=False,
        )

    def disconnect(
        self,
        *,
        owner_subject: str,
        connection_id: str,
    ) -> DisconnectResult:
        record = self._get_owned_record(owner_subject, connection_id)
        secret = self.secret_store.get(record.credential_ref)
        revoked = False

        if secret is not None:
            try:
                settings = self.resolve_settings(
                    owner_subject=owner_subject,
                    connection_id=connection_id,
                )
                with OCSClient(settings) as ocs:
                    ocs.delete_app_password()
                revoked = True
            except (ConnectionError, OCSError):
                # Local disconnect must still complete. The user can independently revoke the
                # app password in Nextcloud if the remote revocation endpoint is unavailable.
                revoked = False

        self.secret_store.delete(record.credential_ref)
        self.connection_store.delete_connection(connection_id)
        return DisconnectResult(
            connection_id=connection_id,
            remote_credential_revoked=revoked,
        )

    def _get_owned_record(self, owner_subject: str, connection_id: str) -> ConnectionRecord:
        subject = self._require_subject(owner_subject)
        record = self.connection_store.get_connection(connection_id)
        if record is None or record.owner_subject != subject:
            # Deliberately identical response for missing vs. foreign records.
            raise ConnectionNotFoundError("Connection was not found")
        return record

    @staticmethod
    def _summary(record: ConnectionRecord) -> ConnectionSummary:
        return ConnectionSummary(
            connection_id=record.connection_id,
            base_url=record.base_url,
            login_name=record.login_name,
            root_path=record.root_path,
            connected_at=record.created_at,
        )
