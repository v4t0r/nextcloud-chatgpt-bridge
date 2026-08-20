from __future__ import annotations

import pytest

from nextcloud_chatgpt_bridge.identity import (
    BridgeIdentity,
    BridgeSessionContext,
    IdentityError,
)


def session(issuer: str, subject: str) -> BridgeSessionContext:
    return BridgeSessionContext(
        identity=BridgeIdentity(issuer=issuer, subject=subject),
        client_id="chatgpt-client",
        scopes=frozenset({"nextcloud:use"}),
    )


def test_tenant_id_is_stable_pseudonymous_and_issuer_scoped():
    first = session("https://auth.example.com/", "user-123")
    repeated = session("https://auth.example.com/", "user-123")
    other_issuer = session("https://other-auth.example.com/", "user-123")

    assert first.tenant_id == repeated.tenant_id
    assert first.tenant_id != other_issuer.tenant_id
    assert "user-123" not in first.tenant_id


def test_session_context_requires_verified_identity_and_client():
    with pytest.raises(IdentityError, match="subject"):
        BridgeIdentity(issuer="https://auth.example.com/", subject=" ")

    with pytest.raises(IdentityError, match="client"):
        BridgeSessionContext(
            identity=BridgeIdentity(
                issuer="https://auth.example.com/",
                subject="user-123",
            ),
            client_id=" ",
            scopes=frozenset(),
        )


def test_session_scope_check_fails_closed():
    context = session("https://auth.example.com/", "user-123")

    context.require_scope("nextcloud:use")
    with pytest.raises(IdentityError, match="required scope"):
        context.require_scope("nextcloud:admin")
