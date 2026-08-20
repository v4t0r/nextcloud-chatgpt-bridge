from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe

from nextcloud_chatgpt_bridge.config import Settings, normalize_root_path
from nextcloud_chatgpt_bridge.connections.login_flow import LoginFlowClient, LoginFlowError
from nextcloud_chatgpt_bridge.connections.models import (
    ConnectionRecord,
    ConnectionSummary,
    ConnectStart,
    DisconnectResult,
    LoginFlowChallenge,
    LoginFlowCredentials,
    PendingLoginRecord,
)
from nextcloud_chatgpt_bridge.connections.store import ConnectionStore, CredentialStore
from nextcloud_chatgpt_bridge.identity import BridgeSessionContext
from nextcloud_chatgpt_bridge.network_policy import PublicHostedPolicy
from nextcloud_chatgpt_bridge.providers.ocs import OCSClient


class ConnectionError(RuntimeError):
    pass


class ConnectionNotFoundError(ConnectionError):
    pass


class ConnectionExpiredError(ConnectionError):
    pass


class ConnectionService:
    """Owns Nextcloud account linking without exposing credentials to MCP/UI metadata."""

    def __init__(
        self,
        *,
        connection_store: ConnectionStore,
        credential_store: CredentialStore,
        login_client: LoginFlowClient,
    ) -> None:
        self.connection_store = connection_store
        self.credential_store = credential_store
        self.login_client = login_client

    def begin_connection(
        self,
        *,
        context: BridgeSessionContext,
        base_url: str,
        root_path: str = "/ChatGPT",
    ) -> ConnectStart:
        root = normalize_root_path(root_path)
        challenge = self.login_client.initiate(base_url)
        flow_id = f"flow_{token_urlsafe(32)}"
        poll_token_ref = self.credential_store.put(context.tenant_id, challenge.poll_token)
        pending = PendingLoginRecord(
            flow_id=flow_id,
            tenant_id=context.tenant_id,
            root_path=root,
            requested_base_url=challenge.requested_base_url,
            login_url=challenge.login_url,
            poll_endpoint=challenge.poll_endpoint,
            poll_token_ref=poll_token_ref,
            expires_at=challenge.expires_at,
        )
        try:
            self.connection_store.put_pending(pending)
        except Exception:
            self.credential_store.delete(context.tenant_id, poll_token_ref)
            raise

        return ConnectStart(
            flow_id=flow_id,
            login_url=challenge.login_url,
            expires_at=challenge.expires_at,
        )

    def poll_connection(
        self,
        *,
        context: BridgeSessionContext,
        flow_id: str,
    ) -> ConnectionSummary | None:
        pending = self.connection_store.get_pending(flow_id, context.tenant_id)
        if pending is None:
            raise ConnectionNotFoundError("Connection flow was not found")
        if datetime.now(UTC) >= pending.expires_at:
            self._delete_pending(pending)
            raise ConnectionExpiredError("Connection flow has expired")

        poll_token = self.credential_store.get(context.tenant_id, pending.poll_token_ref)
        if poll_token is None:
            self._delete_pending(pending)
            raise ConnectionError("Connection flow credential is unavailable")

        challenge = LoginFlowChallenge(
            requested_base_url=pending.requested_base_url,
            login_url=pending.login_url,
            poll_endpoint=pending.poll_endpoint,
            poll_token=poll_token,
            expires_at=pending.expires_at,
        )
        try:
            credentials = self.login_client.poll(challenge)
        except LoginFlowError as exc:
            raise ConnectionError("Nextcloud account linking failed") from exc
        if credentials is None:
            return None

        credential_ref: str | None = None
        try:
            credential_ref = self.credential_store.put(
                context.tenant_id,
                credentials.app_password,
            )
            connection_id = f"nc_{token_urlsafe(32)}"
            record = ConnectionRecord(
                connection_id=connection_id,
                tenant_id=context.tenant_id,
                base_url=credentials.server,
                login_name=credentials.login_name,
                root_path=pending.root_path,
                credential_ref=credential_ref,
                verify_tls=True,
            )
            self.connection_store.put_connection(record)
            return self._summary(record)
        except Exception:
            if credential_ref is not None:
                self.credential_store.delete(context.tenant_id, credential_ref)
            self._best_effort_revoke(credentials, pending.root_path)
            raise
        finally:
            # Nextcloud returns the generated app password only once. Once completion data has
            # arrived the poll flow is consumed whether persistence succeeds or fails.
            self._delete_pending(pending)

    def list_connections(self, *, context: BridgeSessionContext) -> list[ConnectionSummary]:
        return [
            self._summary(record)
            for record in self.connection_store.list_connections(context.tenant_id)
        ]

    def update_root_path(
        self,
        *,
        context: BridgeSessionContext,
        connection_id: str,
        root_path: str,
    ) -> ConnectionSummary:
        record = self._get_owned_record(context, connection_id)
        updated = record.model_copy(update={"root_path": normalize_root_path(root_path)})
        self.connection_store.put_connection(updated)
        return self._summary(updated)

    def resolve_settings(
        self,
        *,
        context: BridgeSessionContext,
        connection_id: str,
    ) -> Settings:
        record = self._get_owned_record(context, connection_id)
        secret = self.credential_store.get(context.tenant_id, record.credential_ref)
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
        context: BridgeSessionContext,
        connection_id: str,
    ) -> DisconnectResult:
        """Disconnect locally even if remote app-password revocation unexpectedly fails."""
        record = self._get_owned_record(context, connection_id)
        secret = self.credential_store.get(context.tenant_id, record.credential_ref)
        revoked = False

        try:
            if secret is not None:
                settings = self.resolve_settings(
                    context=context,
                    connection_id=connection_id,
                )
                with OCSClient(settings) as ocs:
                    ocs.delete_app_password()
                revoked = True
        except Exception:
            revoked = False
        finally:
            self.credential_store.delete(context.tenant_id, record.credential_ref)
            self.connection_store.delete_connection(connection_id, context.tenant_id)

        return DisconnectResult(
            connection_id=connection_id,
            remote_credential_revoked=revoked,
        )

    def _delete_pending(self, pending: PendingLoginRecord) -> None:
        self.credential_store.delete(pending.tenant_id, pending.poll_token_ref)
        self.connection_store.delete_pending(pending.flow_id, pending.tenant_id)

    @staticmethod
    def _best_effort_revoke(credentials: LoginFlowCredentials, root_path: str) -> None:
        try:
            settings = Settings(
                NEXTCLOUD_BASE_URL=str(credentials.server),
                NEXTCLOUD_USERNAME=credentials.login_name,
                NEXTCLOUD_APP_PASSWORD=credentials.app_password.get_secret_value(),
                NEXTCLOUD_ROOT_PATH=root_path,
                NEXTCLOUD_VERIFY_TLS=True,
                NEXTCLOUD_ALLOW_INSECURE_HTTP=False,
            )
            with OCSClient(settings) as ocs:
                ocs.delete_app_password()
        except Exception:
            # Persistence already failed. Do not mask the original exception with cleanup failure.
            return

    def _get_owned_record(
        self,
        context: BridgeSessionContext,
        connection_id: str,
    ) -> ConnectionRecord:
        record = self.connection_store.get_connection(connection_id, context.tenant_id)
        if record is None:
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


def build_hosted_connection_service(
    *,
    connection_store: ConnectionStore,
    credential_store: CredentialStore,
) -> ConnectionService:
    """Compose hosted account linking with the strict public target policy."""
    return ConnectionService(
        connection_store=connection_store,
        credential_store=credential_store,
        login_client=LoginFlowClient(target_policy=PublicHostedPolicy()),
    )
