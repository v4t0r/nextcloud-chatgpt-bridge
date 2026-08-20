from __future__ import annotations

import asyncio
from typing import Any

import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class HostedAuthConfig(BaseSettings):
    """Deployment-owned OAuth/OIDC resource-server configuration.

    These values describe our authorization server, not an end user's Nextcloud.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    issuer_url: AnyHttpUrl = Field(alias="BRIDGE_AUTH_ISSUER_URL")
    jwks_url: AnyHttpUrl = Field(alias="BRIDGE_AUTH_JWKS_URL")
    resource_server_url: AnyHttpUrl = Field(alias="BRIDGE_RESOURCE_SERVER_URL")
    audience: str | None = Field(default=None, alias="BRIDGE_AUTH_AUDIENCE")
    required_scopes: str = Field(default="nextcloud:use", alias="BRIDGE_AUTH_REQUIRED_SCOPES")
    allowed_algorithms: str = Field(default="RS256", alias="BRIDGE_AUTH_ALLOWED_ALGORITHMS")

    @field_validator("issuer_url", "jwks_url", "resource_server_url")
    @classmethod
    def require_https(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https":
            raise ValueError("Hosted OAuth endpoints must use HTTPS")
        return value

    @model_validator(mode="after")
    def fill_and_validate_audience(self) -> HostedAuthConfig:
        if self.audience is None:
            self.audience = str(self.resource_server_url)
        if not self.audience.strip():
            raise ValueError("BRIDGE_AUTH_AUDIENCE must not be empty")
        if not self.scope_list:
            raise ValueError("At least one OAuth scope is required")
        if not self.algorithm_list:
            raise ValueError("At least one JWT algorithm is required")
        return self

    @property
    def scope_list(self) -> list[str]:
        return [scope for scope in self.required_scopes.replace(",", " ").split() if scope]

    @property
    def algorithm_list(self) -> list[str]:
        algorithms = [
            algorithm.strip().upper()
            for algorithm in self.allowed_algorithms.replace(";", ",").split(",")
            if algorithm.strip()
        ]
        for algorithm in algorithms:
            if algorithm == "NONE" or algorithm.startswith("HS"):
                raise ValueError("Unsigned and shared-secret JWT algorithms are not allowed")
        return algorithms


class OIDCTokenVerifier(TokenVerifier):
    """Validate externally issued JWT access tokens using a pinned issuer/audience/JWKS URL."""

    def __init__(self, config: HostedAuthConfig) -> None:
        self.config = config
        self.jwks_client = jwt.PyJWKClient(
            str(config.jwks_url),
            cache_keys=True,
            max_cached_keys=16,
            lifespan=300,
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or len(token) > 16_384:
            return None

        try:
            claims = await asyncio.to_thread(self._decode, token)
        except jwt.PyJWTError:
            return None
        except (OSError, ValueError):
            return None

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            return None

        client_id = claims.get("client_id") or claims.get("azp")
        if not isinstance(client_id, str) or not client_id.strip():
            return None

        scopes = self._parse_scopes(claims)
        required = set(self.config.scope_list)
        if not required.issubset(scopes):
            return None

        expires_at = claims.get("exp")
        if not isinstance(expires_at, int):
            return None

        safe_claims = {
            key: value
            for key, value in claims.items()
            if key in {"iss", "sub", "aud", "azp", "client_id", "scope", "scp"}
        }
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=sorted(scopes),
            expires_at=expires_at,
            resource=self.config.audience,
            subject=subject,
            claims=safe_claims,
        )

    def _decode(self, token: str) -> dict[str, Any]:
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=self.config.algorithm_list,
            audience=self.config.audience,
            issuer=str(self.config.issuer_url),
            options={
                "require": ["exp", "iat", "iss", "aud", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        if not isinstance(claims, dict):
            raise jwt.InvalidTokenError("JWT claims must be an object")
        return claims

    @staticmethod
    def _parse_scopes(claims: dict[str, Any]) -> set[str]:
        raw = claims.get("scope", claims.get("scp", ""))
        if isinstance(raw, str):
            return {scope for scope in raw.split() if scope}
        if isinstance(raw, list) and all(isinstance(scope, str) for scope in raw):
            return {scope for scope in raw if scope}
        return set()


def build_mcp_auth(config: HostedAuthConfig) -> tuple[AuthSettings, OIDCTokenVerifier]:
    """Build RFC 9728 MCP resource-server auth settings plus token verifier."""
    return (
        AuthSettings(
            issuer_url=config.issuer_url,
            resource_server_url=config.resource_server_url,
            required_scopes=config.scope_list,
        ),
        OIDCTokenVerifier(config),
    )

