from __future__ import annotations

from typing import Protocol

from mcp.server.auth.middleware.auth_context import get_access_token

from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.connections.service import ConnectionService


class RuntimeResolutionError(RuntimeError):
    pass


class SettingsResolver(Protocol):
    def resolve(self) -> Settings: ...


class LocalSettingsResolver:
    """Resolve the original single-instance local/self-hosted `.env` configuration."""

    def resolve(self) -> Settings:
        return Settings()


class HostedSettingsResolver:
    """Resolve a Nextcloud connection from the authenticated OAuth subject.

    Initial public-app policy intentionally supports exactly one connected Nextcloud per subject.
    Multi-instance selection will become an explicit user choice rather than an implicit guess.
    """

    def __init__(self, connection_service: ConnectionService) -> None:
        self.connection_service = connection_service

    def resolve(self) -> Settings:
        token = get_access_token()
        if token is None or not token.subject:
            raise RuntimeResolutionError("Authenticated user identity is required")

        connections = self.connection_service.list_connections(owner_subject=token.subject)
        if not connections:
            raise RuntimeResolutionError("No Nextcloud account is connected")
        if len(connections) != 1:
            raise RuntimeResolutionError(
                "Multiple Nextcloud accounts are connected; explicit connection selection is required"
            )

        return self.connection_service.resolve_settings(
            owner_subject=token.subject,
            connection_id=connections[0].connection_id,
        )


def current_oauth_subject() -> str:
    token = get_access_token()
    if token is None or not token.subject:
        raise RuntimeResolutionError("Authenticated user identity is required")
    return token.subject
