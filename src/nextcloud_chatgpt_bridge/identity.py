from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


class IdentityError(ValueError):
    pass


def _required(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise IdentityError(f"{field} is required")
    return normalized


@dataclass(slots=True, frozen=True)
class BridgeIdentity:
    """Verified bridge identity, independent from any Nextcloud account."""

    issuer: str
    subject: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "issuer", _required(self.issuer, "Identity issuer"))
        object.__setattr__(self, "subject", _required(self.subject, "Identity subject"))

    @property
    def tenant_id(self) -> str:
        identity = f"{self.issuer}\x00{self.subject}".encode()
        return f"tenant_{sha256(identity).hexdigest()}"


@dataclass(slots=True, frozen=True)
class BridgeSessionContext:
    """Request-scoped identity and authorization context for one bridge caller."""

    identity: BridgeIdentity
    client_id: str
    scopes: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "client_id", _required(self.client_id, "OAuth client ID"))
        object.__setattr__(
            self,
            "scopes",
            frozenset(scope.strip() for scope in self.scopes if scope.strip()),
        )

    @property
    def tenant_id(self) -> str:
        return self.identity.tenant_id

    def require_scope(self, scope: str) -> None:
        required = _required(scope, "OAuth scope")
        if required not in self.scopes:
            raise IdentityError("Bridge session does not grant the required scope")
