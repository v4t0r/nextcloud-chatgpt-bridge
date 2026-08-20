from __future__ import annotations

from secrets import token_urlsafe

import pytest
from mcp.server import MCPServer
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from nextcloud_chatgpt_bridge.auth import HostedAuthConfig
from nextcloud_chatgpt_bridge.public_app import (
    FixedWindowRateLimiter,
    PublicAppConfig,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    _register_public_routes,
    _trusted_hosts,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def auth_config() -> HostedAuthConfig:
    return HostedAuthConfig(
        BRIDGE_AUTH_ISSUER_URL="https://auth.example.com",
        BRIDGE_AUTH_JWKS_URL="https://auth.example.com/.well-known/jwks.json",
        BRIDGE_RESOURCE_SERVER_URL="https://bridge.example.com/mcp",
        BRIDGE_AUTH_AUDIENCE="https://bridge.example.com/mcp",
    )


def test_trusted_hosts_default_to_resource_host_and_reject_wildcards():
    assert _trusted_hosts(PublicAppConfig(), auth_config()) == ["bridge.example.com"]

    configured = PublicAppConfig(BRIDGE_TRUSTED_HOSTS="bridge.example.com,api.example.com")
    assert _trusted_hosts(configured, auth_config()) == [
        "bridge.example.com",
        "api.example.com",
    ]

    wildcard = PublicAppConfig(BRIDGE_TRUSTED_HOSTS="*.example.com")
    try:
        _trusted_hosts(wildcard, auth_config())
    except ValueError as exc:
        assert "wildcard" in str(exc)
    else:
        raise AssertionError("Wildcard trusted host was accepted")


async def test_rate_limiter_enforces_each_bounded_key():
    limiter = FixedWindowRateLimiter(window_seconds=60, max_keys=3)
    assert await limiter.consume([("ip:one", 2), ("token:one", 1)]) is None
    assert await limiter.consume([("ip:one", 2), ("token:one", 1)]) is not None
    assert len(limiter.windows) <= 3


def test_public_routes_return_exact_challenge_and_readiness():
    challenge_token = token_urlsafe(24)
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE bridge_schema_migrations (version INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO bridge_schema_migrations (version) VALUES (2)"))

    mcp = MCPServer("public-route-test")
    _register_public_routes(
        mcp,
        engine=engine,
        config=PublicAppConfig(OPENAI_APPS_CHALLENGE_TOKEN=challenge_token),
    )
    app = mcp.streamable_http_app(stateless_http=True, host="testserver")

    with TestClient(app) as client:
        challenge = client.get("/.well-known/openai-apps-challenge")
        readiness = client.get("/health/ready")

    assert challenge.status_code == 200
    assert challenge.content == challenge_token.encode()
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"


def test_public_middleware_adds_headers_and_limits_mcp_requests():
    async def endpoint(_request):
        return JSONResponse({"ok": True})

    inner = Starlette(routes=[Route("/mcp", endpoint, methods=["GET"])])
    app = SecurityHeadersMiddleware(
        RateLimitMiddleware(
            inner,
            requests_per_minute=1,
            ip_requests_per_minute=10,
            max_keys=100,
        )
    )
    with TestClient(app) as client:
        first = client.get("/mcp", headers={"Authorization": "Bearer token-a"})
        second = client.get("/mcp", headers={"Authorization": "Bearer token-a"})

    assert first.status_code == 200
    assert first.headers["x-content-type-options"] == "nosniff"
    assert second.status_code == 429
    assert second.json() == {"error": "rate_limit_exceeded"}
