from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import AnyHttpUrl, SecretStr

import nextcloud_chatgpt_bridge.connections.service as service_module
from nextcloud_chatgpt_bridge.connections.models import (
    ConnectionStatus,
    LoginFlowChallenge,
    LoginFlowCredentials,
)
from nextcloud_chatgpt_bridge.connections.service import (
    ConnectionNotFoundError,
    ConnectionService,
    build_hosted_connection_service,
)
from nextcloud_chatgpt_bridge.connections.store import (
    InMemoryConnectionStore,
    InMemoryCredentialStore,
)
from nextcloud_chatgpt_bridge.identity import BridgeIdentity, BridgeSessionContext
from nextcloud_chatgpt_bridge.network_policy import PublicHostedPolicy


class FakeLoginFlowClient:
    def __init__(self) -> None:
        self.initiated: list[str] = []
        self.completed = True

    def initiate(self, base_url: str) -> LoginFlowChallenge:
        self.initiated.append(base_url)
        return LoginFlowChallenge(
            requested_base_url=AnyHttpUrl("https://cloud.example.com"),
            login_url=AnyHttpUrl("https://cloud.example.com/login/v2/flow/abc"),
            poll_endpoint=AnyHttpUrl("https://cloud.example.com/login/v2/poll"),
            poll_token=SecretStr("poll-secret"),
            expires_at=datetime.now(UTC) + timedelta(minutes=20),
        )

    def poll(self, challenge: LoginFlowChallenge) -> LoginFlowCredentials | None:
        if not self.completed:
            return None
        return LoginFlowCredentials(
            server=AnyHttpUrl("https://cloud.example.com"),
            login_name="bridge-user",
            app_password=SecretStr("generated-app-password"),
        )


def make_service() -> tuple[
    ConnectionService,
    InMemoryConnectionStore,
    InMemoryCredentialStore,
    FakeLoginFlowClient,
]:
    connections = InMemoryConnectionStore()
    secrets = InMemoryCredentialStore()
    login = FakeLoginFlowClient()
    return (
        ConnectionService(
            connection_store=connections,
            credential_store=secrets,
            login_client=login,  # type: ignore[arg-type]
        ),
        connections,
        secrets,
        login,
    )


def session(owner: str, issuer: str = "https://auth.example.com/") -> BridgeSessionContext:
    return BridgeSessionContext(
        identity=BridgeIdentity(issuer=issuer, subject=owner),
        client_id="chatgpt-client",
        scopes=frozenset({"nextcloud:use"}),
    )


def connect(service: ConnectionService, *, owner: str = "user-a"):
    started = service.begin_connection(
        context=session(owner),
        base_url="https://cloud.example.com",
        root_path="/ChatGPT",
    )
    completed = service.poll_connection(context=session(owner), flow_id=started.flow_id)
    assert completed is not None
    return started, completed


def test_connect_start_does_not_expose_poll_token_or_app_password():
    service, _, _, _ = make_service()
    started = service.begin_connection(
        context=session("user-a"),
        base_url="https://cloud.example.com",
    )

    serialized = started.model_dump_json()
    assert started.status is ConnectionStatus.PENDING
    assert "poll-secret" not in serialized
    assert "appPassword" not in serialized
    assert "login/v2/flow/abc" in serialized


def test_pending_metadata_contains_only_poll_secret_reference():
    service, store, secrets, _ = make_service()
    started = service.begin_connection(
        context=session("user-a"),
        base_url="https://cloud.example.com",
    )

    pending = store.get_pending(started.flow_id, session("user-a").tenant_id)
    assert pending is not None
    assert "poll-secret" not in pending.model_dump_json()
    secret = secrets.get(session("user-a").tenant_id, pending.poll_token_ref)
    assert secret is not None
    assert secret.get_secret_value() == "poll-secret"


def test_completed_connection_separates_metadata_from_secret_and_consumes_poll_secret():
    service, store, secrets, _ = make_service()
    started = service.begin_connection(
        context=session("user-a"),
        base_url="https://cloud.example.com",
    )
    pending = store.get_pending(started.flow_id, session("user-a").tenant_id)
    assert pending is not None
    poll_token_ref = pending.poll_token_ref

    completed = service.poll_connection(context=session("user-a"), flow_id=started.flow_id)
    assert completed is not None
    assert completed.status is ConnectionStatus.CONNECTED
    record = store.get_connection(completed.connection_id, session("user-a").tenant_id)
    assert record is not None
    assert "generated-app-password" not in record.model_dump_json()
    stored_secret = secrets.get(session("user-a").tenant_id, record.credential_ref)
    assert stored_secret is not None
    assert stored_secret.get_secret_value() == "generated-app-password"
    assert secrets.get(session("user-b").tenant_id, record.credential_ref) is None
    assert secrets.get(session("user-a").tenant_id, poll_token_ref) is None
    assert store.get_pending(started.flow_id, session("user-a").tenant_id) is None

    settings = service.resolve_settings(
        context=session("user-a"),
        connection_id=completed.connection_id,
    )
    assert settings.nextcloud_username == "bridge-user"
    assert settings.nextcloud_app_password.get_secret_value() == "generated-app-password"
    assert settings.nextcloud_root_path == "/ChatGPT"


def test_foreign_user_cannot_resolve_or_poll_another_users_connection():
    service, store, _, login = make_service()
    started = service.begin_connection(
        context=session("user-a"),
        base_url="https://cloud.example.com",
    )

    assert store.get_pending(started.flow_id, session("user-b").tenant_id) is None
    with pytest.raises(ConnectionNotFoundError):
        service.poll_connection(context=session("user-b"), flow_id=started.flow_id)

    completed = service.poll_connection(context=session("user-a"), flow_id=started.flow_id)
    assert completed is not None
    assert login.completed is True
    assert store.get_connection(completed.connection_id, session("user-b").tenant_id) is None

    with pytest.raises(ConnectionNotFoundError):
        service.resolve_settings(
            context=session("user-b"),
            connection_id=completed.connection_id,
        )
    assert service.list_connections(context=session("user-b")) == []


def test_root_scope_is_validated_before_starting_remote_login():
    service, _, _, login = make_service()
    with pytest.raises(ValueError):
        service.begin_connection(
            context=session("user-a"),
            base_url="https://cloud.example.com",
            root_path="/",
        )
    assert login.initiated == []


def test_poll_can_remain_pending_without_creating_connection_or_losing_poll_secret():
    service, store, secrets, login = make_service()
    login.completed = False
    started = service.begin_connection(
        context=session("user-a"),
        base_url="https://cloud.example.com",
    )
    pending = store.get_pending(started.flow_id, session("user-a").tenant_id)
    assert pending is not None

    assert service.poll_connection(context=session("user-a"), flow_id=started.flow_id) is None
    assert list(store.list_connections(session("user-a").tenant_id)) == []
    assert store.get_pending(started.flow_id, session("user-a").tenant_id) is not None
    assert secrets.get(session("user-a").tenant_id, pending.poll_token_ref) is not None


def test_disconnect_revokes_remote_credential_then_removes_local_secret(monkeypatch):
    service, store, secrets, _ = make_service()
    _, completed = connect(service)
    record = store.get_connection(completed.connection_id, session("user-a").tenant_id)
    assert record is not None
    revoked: list[str] = []

    class FakeOCSClient:
        def __init__(self, settings):
            assert settings.nextcloud_app_password.get_secret_value() == "generated-app-password"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def delete_app_password(self) -> None:
            revoked.append("yes")

    monkeypatch.setattr(service_module, "OCSClient", FakeOCSClient)

    result = service.disconnect(
        context=session("user-a"),
        connection_id=completed.connection_id,
    )

    assert result.status is ConnectionStatus.DISCONNECTED
    assert result.remote_credential_revoked is True
    assert revoked == ["yes"]
    assert store.get_connection(completed.connection_id, session("user-a").tenant_id) is None
    assert secrets.get(session("user-a").tenant_id, record.credential_ref) is None


def test_disconnect_still_purges_local_secret_on_unexpected_remote_failure(monkeypatch):
    service, store, secrets, _ = make_service()
    _, completed = connect(service)
    record = store.get_connection(completed.connection_id, session("user-a").tenant_id)
    assert record is not None

    class ExplodingOCSClient:
        def __init__(self, settings):
            pass

        def __enter__(self):
            raise RuntimeError("unexpected library failure")

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(service_module, "OCSClient", ExplodingOCSClient)

    result = service.disconnect(
        context=session("user-a"),
        connection_id=completed.connection_id,
    )

    assert result.remote_credential_revoked is False
    assert store.get_connection(completed.connection_id, session("user-a").tenant_id) is None
    assert secrets.get(session("user-a").tenant_id, record.credential_ref) is None


def test_hosted_service_builder_binds_public_target_policy():
    service = build_hosted_connection_service(
        connection_store=InMemoryConnectionStore(),
        credential_store=InMemoryCredentialStore(),
    )

    try:
        assert isinstance(service.login_client.target_policy, PublicHostedPolicy)
    finally:
        service.login_client.close()

