from __future__ import annotations

import argparse
import asyncio
import hashlib
import math
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.engine import Engine
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from nextcloud_chatgpt_bridge import __version__
from nextcloud_chatgpt_bridge.auth import HostedAuthConfig
from nextcloud_chatgpt_bridge.connections.service import build_hosted_connection_service
from nextcloud_chatgpt_bridge.hosted_server import create_hosted_mcp
from nextcloud_chatgpt_bridge.household.service import HouseholdService
from nextcloud_chatgpt_bridge.persistence import HostedStorageConfig, build_hosted_store_bundle
from nextcloud_chatgpt_bridge.schema import verify_hosted_schema


class PublicAppConfig(BaseSettings):
    """Non-secret operational settings for the public MCP process."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1", alias="BRIDGE_HOST")
    port: int = Field(default=8000, ge=1, le=65535, alias="PORT")
    log_level: Literal["critical", "error", "warning", "info"] = Field(
        default="info",
        alias="BRIDGE_LOG_LEVEL",
    )
    trusted_hosts: str = Field(default="", alias="BRIDGE_TRUSTED_HOSTS")
    allowed_origins: str = Field(default="", alias="BRIDGE_ALLOWED_ORIGINS")
    challenge_token: SecretStr | None = Field(
        default=None,
        alias="OPENAI_APPS_CHALLENGE_TOKEN",
    )
    requests_per_minute: int = Field(
        default=180,
        ge=10,
        le=10_000,
        alias="BRIDGE_RATE_LIMIT_REQUESTS_PER_MINUTE",
    )
    ip_requests_per_minute: int = Field(
        default=1_200,
        ge=10,
        le=100_000,
        alias="BRIDGE_RATE_LIMIT_IP_REQUESTS_PER_MINUTE",
    )
    rate_limit_max_keys: int = Field(
        default=20_000,
        ge=100,
        le=1_000_000,
        alias="BRIDGE_RATE_LIMIT_MAX_KEYS",
    )
    max_request_body_bytes: int = Field(
        default=4 * 1024 * 1024,
        ge=64 * 1024,
        le=16 * 1024 * 1024,
        alias="BRIDGE_MAX_REQUEST_BODY_BYTES",
    )
    website_url: str = Field(
        default="https://github.com/v4t0r/nextcloud-chatgpt-bridge",
        alias="BRIDGE_WEBSITE_URL",
    )
    support_url: str = Field(
        default="https://github.com/v4t0r/nextcloud-chatgpt-bridge/issues",
        alias="BRIDGE_SUPPORT_URL",
    )

    @field_validator("trusted_hosts", "allowed_origins", "website_url", "support_url")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise ValueError("Public app configuration contains control characters")
        return value.strip()

    @field_validator("challenge_token", mode="before")
    @classmethod
    def empty_challenge_is_disabled(cls, value):
        if value is None or value == "":
            return None
        return value

    @field_validator("website_url", "support_url")
    @classmethod
    def require_public_https_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Public product URLs must use HTTPS without embedded credentials")
        return value

    @property
    def configured_trusted_hosts(self) -> list[str]:
        return [host.strip().lower() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def configured_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@dataclass(slots=True)
class _RateWindow:
    started_at: float
    requests: int


class FixedWindowRateLimiter:
    """Bounded in-process limiter for the single-worker public deployment profile."""

    def __init__(self, *, window_seconds: int = 60, max_keys: int = 20_000) -> None:
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self.windows: OrderedDict[str, _RateWindow] = OrderedDict()
        self.lock = asyncio.Lock()

    async def consume(self, limits: list[tuple[str, int]]) -> int | None:
        now = time.monotonic()
        async with self.lock:
            active: list[tuple[str, int, _RateWindow]] = []
            for key, limit in limits:
                window = self.windows.get(key)
                if window is None or now - window.started_at >= self.window_seconds:
                    window = _RateWindow(started_at=now, requests=0)
                if window.requests >= limit:
                    return max(1, math.ceil(self.window_seconds - (now - window.started_at)))
                active.append((key, limit, window))

            for key, _limit, window in active:
                window.requests += 1
                self.windows[key] = window
                self.windows.move_to_end(key)
            while len(self.windows) > self.max_keys:
                self.windows.popitem(last=False)
        return None


class RateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        requests_per_minute: int,
        ip_requests_per_minute: int,
        max_keys: int,
    ) -> None:
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.ip_requests_per_minute = ip_requests_per_minute
        self.limiter = FixedWindowRateLimiter(max_keys=max_keys)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_address = client[0] if client else "unknown"
        limits = [(f"ip:{client_address}", self.ip_requests_per_minute)]
        authorization = _header_value(scope, b"authorization")
        if authorization and authorization.lower().startswith(b"bearer "):
            token = authorization[7:].strip()
            if token:
                digest = hashlib.sha256(token).hexdigest()
                limits.append((f"token:{digest}", self.requests_per_minute))

        retry_after = await self.limiter.consume(limits)
        if retry_after is not None:
            response = JSONResponse(
                {"error": "rate_limit_exceeded"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"strict-transport-security", b"max-age=31536000"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _header_value(scope: Scope, name: bytes) -> bytes | None:
    for header_name, value in scope.get("headers", []):
        if header_name.lower() == name:
            return value
    return None


def _trusted_hosts(config: PublicAppConfig, auth_config: HostedAuthConfig) -> list[str]:
    resource_host = (urlsplit(str(auth_config.resource_server_url)).hostname or "").lower()
    configured = config.configured_trusted_hosts
    if any(host == "*" or host.startswith("*.") for host in configured):
        raise ValueError("BRIDGE_TRUSTED_HOSTS must not contain wildcard hosts")
    hosts = configured or [resource_host]
    if not resource_host or resource_host not in hosts:
        raise ValueError("BRIDGE_TRUSTED_HOSTS must include the MCP resource host")
    return hosts


def _register_public_routes(
    mcp: MCPServer,
    *,
    engine: Engine,
    config: PublicAppConfig,
) -> None:
    @mcp.custom_route("/", methods=["GET"], include_in_schema=False)
    async def product_info(_request: Request) -> Response:
        return JSONResponse(
            {
                "name": "Nextcloud for ChatGPT & Codex",
                "version": __version__,
                "mcp": "/mcp",
                "website": config.website_url,
                "support": config.support_url,
            }
        )

    @mcp.custom_route("/health/live", methods=["GET"], include_in_schema=False)
    async def liveness(_request: Request) -> Response:
        return JSONResponse({"status": "ok", "version": __version__})

    @mcp.custom_route("/health/ready", methods=["GET"], include_in_schema=False)
    async def readiness(_request: Request) -> Response:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            verify_hosted_schema(engine)
        except Exception:
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return JSONResponse({"status": "ready", "version": __version__})

    @mcp.custom_route(
        "/.well-known/openai-apps-challenge",
        methods=["GET"],
        include_in_schema=False,
    )
    async def openai_apps_challenge(_request: Request) -> Response:
        if config.challenge_token is None:
            return Response(status_code=404)
        return PlainTextResponse(
            config.challenge_token.get_secret_value(),
            media_type="text/plain",
        )


def create_public_app(
    *,
    public_config: PublicAppConfig | None = None,
    auth_config: HostedAuthConfig | None = None,
    storage_config: HostedStorageConfig | None = None,
) -> Starlette:
    """Compose the production-facing, OAuth-protected universal MCP application."""
    public = public_config or PublicAppConfig()
    auth = auth_config or HostedAuthConfig()
    storage = storage_config or HostedStorageConfig()
    stores = build_hosted_store_bundle(storage)
    verify_hosted_schema(stores.engine)

    connection_service = build_hosted_connection_service(
        connection_store=stores.connection_store,
        credential_store=stores.credential_store,
    )
    household_service = HouseholdService(
        profile_store=stores.household_store,
        settings_provider=connection_service,
    )
    mcp = create_hosted_mcp(
        connection_service=connection_service,
        auth_config=auth,
        household_service=household_service,
    )
    _register_public_routes(mcp, engine=stores.engine, config=public)

    trusted_hosts = _trusted_hosts(public, auth)
    transport_hosts = [value for host in trusted_hosts for value in (host, f"{host}:*")]
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        max_request_body_size=public.max_request_body_bytes,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=transport_hosts,
            allowed_origins=public.configured_allowed_origins,
        ),
        host=public.host,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=public.requests_per_minute,
        ip_requests_per_minute=public.ip_requests_per_minute,
        max_keys=public.rate_limit_max_keys,
    )
    app.state.bridge_engine = stores.engine
    app.state.bridge_connection_service = connection_service
    return app


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Run the public OAuth-protected Nextcloud MCP application."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args()

    config = PublicAppConfig()
    uvicorn.run(
        create_public_app(public_config=config),
        host=config.host,
        port=config.port,
        log_level=config.log_level,
        access_log=False,
        server_header=False,
        workers=1,
    )


if __name__ == "__main__":
    main()
