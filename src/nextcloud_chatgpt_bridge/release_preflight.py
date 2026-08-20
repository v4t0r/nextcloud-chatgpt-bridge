from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal
from urllib.parse import urljoin, urlsplit

import httpx
from mcp.server.auth.routes import build_resource_metadata_url
from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from nextcloud_chatgpt_bridge import __version__


@dataclass(slots=True, frozen=True)
class PreflightCheck:
    name: str
    passed: bool
    detail: str


class ReleasePreflightConfig(BaseSettings):
    """Public, non-credential release endpoints plus the domain challenge token."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        url_preserve_empty_path=True,
    )

    mcp_url: AnyHttpUrl = Field(alias="BRIDGE_RESOURCE_SERVER_URL")
    issuer_url: AnyHttpUrl = Field(alias="BRIDGE_AUTH_ISSUER_URL")
    oauth_discovery_url: AnyHttpUrl = Field(alias="BRIDGE_AUTH_DISCOVERY_URL")
    required_scopes: str = Field(default="nextcloud:use", alias="BRIDGE_AUTH_REQUIRED_SCOPES")
    oauth_client_mode: Literal["cimd", "dcr", "predefined"] = Field(
        default="cimd",
        alias="BRIDGE_AUTH_CLIENT_MODE",
    )
    require_userinfo: bool = Field(default=False, alias="BRIDGE_AUTH_REQUIRE_USERINFO")
    website_url: AnyHttpUrl = Field(alias="BRIDGE_WEBSITE_URL")
    support_url: AnyHttpUrl = Field(alias="BRIDGE_SUPPORT_URL")
    privacy_url: AnyHttpUrl = Field(alias="BRIDGE_PRIVACY_URL")
    terms_url: AnyHttpUrl = Field(alias="BRIDGE_TERMS_URL")
    challenge_token: SecretStr | None = Field(
        default=None,
        alias="OPENAI_APPS_CHALLENGE_TOKEN",
    )

    @field_validator("challenge_token", mode="before")
    @classmethod
    def empty_challenge_is_disabled(cls, value):
        if value is None or value == "":
            return None
        return value

    @property
    def scope_list(self) -> list[str]:
        return [scope for scope in self.required_scopes.replace(",", " ").split() if scope]


def _https_endpoint(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
    )


def validate_resource_metadata(
    document: dict[str, Any],
    config: ReleasePreflightConfig,
) -> list[PreflightCheck]:
    authorization_servers = document.get("authorization_servers")
    scopes = document.get("scopes_supported")
    return [
        PreflightCheck(
            "resource_metadata.resource",
            document.get("resource") == str(config.mcp_url),
            "resource identifier matches the universal MCP URL",
        ),
        PreflightCheck(
            "resource_metadata.authorization_server",
            isinstance(authorization_servers, list)
            and str(config.issuer_url) in authorization_servers,
            "authorization server contains the configured exact issuer",
        ),
        PreflightCheck(
            "resource_metadata.scopes",
            isinstance(scopes, list) and set(config.scope_list).issubset(scopes),
            "protected resource metadata advertises every required scope",
        ),
    ]


def validate_oauth_metadata(
    document: dict[str, Any],
    config: ReleasePreflightConfig,
) -> list[PreflightCheck]:
    methods = document.get("token_endpoint_auth_methods_supported")
    scopes = document.get("scopes_supported")
    checks = [
        PreflightCheck(
            "oauth.issuer",
            document.get("issuer") == str(config.issuer_url),
            "OAuth discovery issuer matches exactly",
        ),
        PreflightCheck(
            "oauth.authorization_endpoint",
            _https_endpoint(document.get("authorization_endpoint")),
            "authorization endpoint is public HTTPS",
        ),
        PreflightCheck(
            "oauth.token_endpoint",
            _https_endpoint(document.get("token_endpoint")),
            "token endpoint is public HTTPS",
        ),
        PreflightCheck(
            "oauth.pkce_s256",
            "S256" in document.get("code_challenge_methods_supported", []),
            "OAuth metadata advertises PKCE S256",
        ),
        PreflightCheck(
            "oauth.scopes",
            isinstance(scopes, list) and set(config.scope_list).issubset(scopes),
            "OAuth provider advertises every bridge scope",
        ),
    ]

    if config.oauth_client_mode == "cimd":
        checks.append(
            PreflightCheck(
                "oauth.client_registration",
                document.get("client_id_metadata_document_supported") is True
                and isinstance(methods, list)
                and bool({"none", "private_key_jwt"}.intersection(methods)),
                "CIMD is enabled with a ChatGPT-compatible token authentication method",
            )
        )
    elif config.oauth_client_mode == "dcr":
        checks.append(
            PreflightCheck(
                "oauth.client_registration",
                _https_endpoint(document.get("registration_endpoint")),
                "dynamic client registration endpoint is public HTTPS",
            )
        )
    else:
        checks.append(
            PreflightCheck(
                "oauth.client_registration",
                isinstance(methods, list)
                and bool(
                    {
                        "none",
                        "private_key_jwt",
                        "client_secret_post",
                        "client_secret_basic",
                    }.intersection(methods)
                ),
                "predefined client mode has a supported token authentication method",
            )
        )

    if config.require_userinfo:
        checks.extend(
            [
                PreflightCheck(
                    "oauth.userinfo_endpoint",
                    _https_endpoint(document.get("userinfo_endpoint")),
                    "UserInfo endpoint is public HTTPS",
                ),
                PreflightCheck(
                    "oauth.userinfo_scopes",
                    isinstance(scopes, list) and {"openid", "email"}.issubset(scopes),
                    "openid and email scopes are advertised",
                ),
            ]
        )
    return checks


def _bounded_json(response: httpx.Response) -> dict[str, Any]:
    if len(response.content) > 1024 * 1024:
        raise ValueError("JSON response exceeded the release preflight limit")
    parsed = response.json()
    if not isinstance(parsed, dict):
        raise ValueError("JSON response was not an object")
    return parsed


def _public_origin(url: AnyHttpUrl) -> str:
    parsed = urlsplit(str(url))
    return f"{parsed.scheme}://{parsed.netloc}/"


def run_release_preflight(config: ReleasePreflightConfig) -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    origin = _public_origin(config.mcp_url)
    metadata_url = str(build_resource_metadata_url(config.mcp_url))
    client = httpx.Client(
        timeout=httpx.Timeout(15.0, read=30.0),
        follow_redirects=False,
        headers={"User-Agent": "nextcloud-chatgpt-bridge-release-preflight"},
    )
    try:
        liveness = client.get(urljoin(origin, "health/live"))
        checks.append(
            PreflightCheck(
                "mcp.liveness",
                liveness.status_code == 200,
                "public liveness endpoint responds successfully",
            )
        )
        readiness = client.get(urljoin(origin, "health/ready"))
        checks.append(
            PreflightCheck(
                "mcp.readiness",
                readiness.status_code == 200,
                "database and schema readiness succeeds",
            )
        )

        resource_response = client.get(metadata_url)
        if resource_response.status_code == 200:
            checks.extend(validate_resource_metadata(_bounded_json(resource_response), config))
        else:
            checks.append(
                PreflightCheck(
                    "resource_metadata.available",
                    False,
                    "protected resource metadata endpoint is unavailable",
                )
            )

        unauthorized = client.post(
            str(config.mcp_url),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "release-preflight", "version": "1"},
                },
            },
        )
        challenge = unauthorized.headers.get("www-authenticate", "")
        checks.append(
            PreflightCheck(
                "mcp.oauth_challenge",
                unauthorized.status_code == 401 and metadata_url in challenge,
                "unauthenticated MCP requests advertise protected resource metadata",
            )
        )

        oauth_response = client.get(str(config.oauth_discovery_url))
        if oauth_response.status_code == 200:
            checks.extend(validate_oauth_metadata(_bounded_json(oauth_response), config))
        else:
            checks.append(
                PreflightCheck(
                    "oauth.discovery",
                    False,
                    "OAuth discovery endpoint is unavailable",
                )
            )

        for name, url in (
            ("website", config.website_url),
            ("support", config.support_url),
            ("privacy", config.privacy_url),
            ("terms", config.terms_url),
        ):
            response = client.get(str(url), follow_redirects=True)
            checks.append(
                PreflightCheck(
                    f"public_url.{name}",
                    response.status_code == 200 and urlsplit(str(response.url)).scheme == "https",
                    f"{name} URL is publicly reachable over HTTPS",
                )
            )

        if config.challenge_token is not None:
            response = client.get(urljoin(origin, ".well-known/openai-apps-challenge"))
            checks.append(
                PreflightCheck(
                    "openai.domain_challenge",
                    response.status_code == 200
                    and response.content
                    == config.challenge_token.get_secret_value().encode("utf-8"),
                    "domain challenge returns exactly the configured token",
                )
            )
    except (httpx.HTTPError, ValueError, UnicodeError):
        checks.append(
            PreflightCheck(
                "preflight.transport",
                False,
                "a public endpoint failed transport or response validation",
            )
        )
    finally:
        client.close()
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the public endpoints required for app submission."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args()

    checks = run_release_preflight(ReleasePreflightConfig())
    failed = [check.name for check in checks if not check.passed]
    print(
        json.dumps(
            {
                "ok": not failed,
                "failed_checks": failed,
                "checks": [asdict(check) for check in checks],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
