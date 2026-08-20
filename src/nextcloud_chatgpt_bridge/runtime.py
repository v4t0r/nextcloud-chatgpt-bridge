from __future__ import annotations

from typing import Protocol

from mcp.server.auth.middleware.auth_context import get_access_token

from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.connections.service import ConnectionService
from nextcloud_chatgpt_bridge.identity import BridgeIdentity, BridgeSessionContext, IdentityError


class RuntimeResolutionError(RuntimeError):
    pass


class SettingsResolver(Protocol):
    def resolve(self) -> Settings: ...


class LocalSettingsResolver:
    """Resolve the original single-instance local/self-hosted `.env` configuration."""

    def resolve(self) -> Settings:
        return Settings()


class HostedSettingsResolver:
    """Resolve a Nextcloud connection from the request-scoped bridge session.

    Initial public-app policy intentionally supports exactly one connected Nextcloud per tenant.
    Multi-instance selection will become an explicit user choice rather than an implicit guess.
    """

    def __init__(self, connection_service: ConnectionService) -> None:
        self.connection_service = connection_service

    def resolve(self) -> Settings:
        context = current_session_context()

        connections = self.connection_service.list_connections(context=context)
        if not connections:
            raise RuntimeResolutionError("No Nextcloud account is connected")
        if len(connections) != 1:
            raise RuntimeResolutionError(
                "Multiple Nextcloud accounts are connected; explicit connection selection is required"
            )

        return self.connection_service.resolve_settings(
            context=context,
            connection_id=connections[0].connection_id,
        )


def current_session_context() -> BridgeSessionContext:
    """Build a fresh bridge session from the MCP auth context for every request."""
    token = get_access_token()
    if token is None or not token.subject or not token.client_id:
        raise RuntimeResolutionError("Authenticated user identity is required")
    claims = token.claims or {}
    issuer = claims.get("iss")
    if not isinstance(issuer, str):
        raise RuntimeResolutionError("Authenticated identity issuer is required")
    try:
        return BridgeSessionContext(
            identity=BridgeIdentity(issuer=issuer, subject=token.subject),
            client_id=token.client_id,
            scopes=frozenset(token.scopes),
        )
    except IdentityError as exc:
        raise RuntimeResolutionError("Authenticated user identity is invalid") from exc
