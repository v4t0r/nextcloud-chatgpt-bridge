from __future__ import annotations

from datetime import UTC, datetime

import pytest
from mcp.server.auth.provider import AccessToken
from pydantic import AnyHttpUrl

import nextcloud_chatgpt_bridge.runtime as runtime
from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.connections.models import ConnectionSummary
from nextcloud_chatgpt_bridge.runtime import HostedSettingsResolver, RuntimeResolutionError


class FakeConnectionService:
    def __init__(self, connections: list[ConnectionSummary]) -> None:
        self.connections = connections
        self.resolved: list[tuple[str, str]] = []

    def list_connections(self, *, context):
        return self.connections

    def resolve_settings(self, *, context, connection_id: str) -> Settings:
        self.resolved.append((context.tenant_id, connection_id))
        return Settings(
            NEXTCLOUD_BASE_URL="https://cloud.example.com",
            NEXTCLOUD_USERNAME="bridge-user",
            NEXTCLOUD_APP_PASSWORD="secret",  # noqa: S106
            NEXTCLOUD_ROOT_PATH="/ChatGPT",
        )


def token(
    subject: str | None = "user-a",
    issuer: str = "https://auth.example.com/",
) -> AccessToken:
    return AccessToken(
        token="bearer",  # noqa: S106
        client_id="chatgpt-client",
        scopes=["nextcloud:use"],
        subject=subject,
        claims={"iss": issuer},
    )


def summary(connection_id: str = "nc_connection_1234567890") -> ConnectionSummary:
    return ConnectionSummary(
        connection_id=connection_id,
        base_url=AnyHttpUrl("https://cloud.example.com"),
        login_name="bridge-user",
        root_path="/ChatGPT",
        connected_at=datetime.now(UTC),
    )


def test_hosted_resolver_uses_authenticated_subject_and_single_connection(monkeypatch):
    service = FakeConnectionService([summary()])
    monkeypatch.setattr(runtime, "get_access_token", lambda: token())

    settings = HostedSettingsResolver(service).resolve()  # type: ignore[arg-type]

    assert settings.nextcloud_username == "bridge-user"
    assert service.resolved == [
        (runtime.current_session_context().tenant_id, "nc_connection_1234567890")
    ]


def test_hosted_resolver_fails_closed_without_authenticated_subject(monkeypatch):
    service = FakeConnectionService([summary()])
    monkeypatch.setattr(runtime, "get_access_token", lambda: token(None))

    with pytest.raises(RuntimeResolutionError, match="identity"):
        HostedSettingsResolver(service).resolve()  # type: ignore[arg-type]


def test_hosted_resolver_fails_closed_with_no_connection(monkeypatch):
    service = FakeConnectionService([])
    monkeypatch.setattr(runtime, "get_access_token", lambda: token())

    with pytest.raises(RuntimeResolutionError, match="No Nextcloud"):
        HostedSettingsResolver(service).resolve()  # type: ignore[arg-type]


def test_hosted_resolver_never_guesses_between_multiple_connections(monkeypatch):
    service = FakeConnectionService([summary("nc_connection_1111111111"), summary("nc_connection_2222222222")])
    monkeypatch.setattr(runtime, "get_access_token", lambda: token())

    with pytest.raises(RuntimeResolutionError, match="explicit connection selection"):
        HostedSettingsResolver(service).resolve()  # type: ignore[arg-type]




def test_session_context_is_issuer_scoped(monkeypatch):
    first = token()
    second = token(issuer="https://other-auth.example.com/")

    monkeypatch.setattr(runtime, "get_access_token", lambda: first)
    first_tenant = runtime.current_session_context().tenant_id
    monkeypatch.setattr(runtime, "get_access_token", lambda: second)
    second_tenant = runtime.current_session_context().tenant_id

    assert first_tenant != second_tenant
