"""Multi-user Nextcloud connection lifecycle and credential isolation."""

from nextcloud_chatgpt_bridge.connections.models import (
    ConnectionStatus,
    ConnectionSummary,
    ConnectStart,
    DisconnectResult,
)
from nextcloud_chatgpt_bridge.connections.service import (
    ConnectionService,
    build_hosted_connection_service,
)

__all__ = [
    "ConnectStart",
    "ConnectionService",
    "ConnectionStatus",
    "ConnectionSummary",
    "DisconnectResult",
    "build_hosted_connection_service",
]
