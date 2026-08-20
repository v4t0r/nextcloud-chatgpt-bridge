from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import AnyHttpUrl, SecretStr

from nextcloud_chatgpt_bridge.connections.models import (
    LoginFlowChallenge,
    LoginFlowCredentials,
)
from nextcloud_chatgpt_bridge.network_policy import LocalSelfHostedPolicy, TargetPolicy

_MAX_LOGIN_RESPONSE_BYTES = 128 * 1024
_LOGIN_FLOW_TTL = timedelta(minutes=20)


class LoginFlowError(RuntimeError):
    pass


def _origin(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if not host:
        raise LoginFlowError("Nextcloud URL is missing a hostname")
    default_port = 443 if scheme == "https" else 80
    return scheme, host, parsed.port or default_port


def _validate_base_url(value: str, *, allow_insecure_http: bool = False) -> str:
    raw = value.strip().rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme not in ({"https", "http"} if allow_insecure_http else {"https"}):
        raise LoginFlowError("Nextcloud connection requires HTTPS")
    if not parsed.hostname:
        raise LoginFlowError("Nextcloud URL is missing a hostname")
    if parsed.username or parsed.password:
        raise LoginFlowError("Credentials must not be embedded in the Nextcloud URL")
    if parsed.query or parsed.fragment:
        raise LoginFlowError("Nextcloud URL must not contain query parameters or fragments")
    return raw


def _require_same_origin(candidate: str, expected_base: str) -> None:
    if _origin(candidate) != _origin(expected_base):
        raise LoginFlowError("Nextcloud Login Flow returned a cross-origin URL")


def _read_bounded_json(response: httpx.Response) -> dict[str, Any]:
    data = bytearray()
    for chunk in response.iter_bytes():
        data.extend(chunk)
        if len(data) > _MAX_LOGIN_RESPONSE_BYTES:
            raise LoginFlowError("Nextcloud Login Flow response exceeded the safety limit")
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LoginFlowError("Nextcloud Login Flow returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise LoginFlowError("Nextcloud Login Flow returned an unexpected response shape")
    return parsed


class LoginFlowClient:
    """Nextcloud Login Flow v2 client with strict origin, target and size boundaries."""

    def __init__(
        self,
        *,
        allow_insecure_http: bool = False,
        target_policy: TargetPolicy | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.allow_insecure_http = allow_insecure_http
        self.target_policy = target_policy or LocalSelfHostedPolicy(
            allow_insecure_http=allow_insecure_http
        )
        self.client = httpx.Client(
            timeout=httpx.Timeout(15.0, read=30.0),
            follow_redirects=False,
            transport=transport,
            headers={"User-Agent": "nextcloud-chatgpt-bridge/0.1"},
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> LoginFlowClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def initiate(self, base_url: str) -> LoginFlowChallenge:
        base = _validate_base_url(base_url, allow_insecure_http=self.allow_insecure_http)
        self.target_policy.validate_url(base)
        endpoint = f"{base}/index.php/login/v2"

        with self.client.stream("POST", endpoint) as response:
            if response.status_code != 200:
                raise LoginFlowError(
                    f"Nextcloud Login Flow initialization returned HTTP {response.status_code}"
                )
            payload = _read_bounded_json(response)

        poll = payload.get("poll")
        login = payload.get("login")
        if not isinstance(poll, dict) or not isinstance(login, str):
            raise LoginFlowError("Nextcloud Login Flow initialization is missing login/poll data")

        token = poll.get("token")
        poll_endpoint = poll.get("endpoint")
        if not isinstance(token, str) or not token or not isinstance(poll_endpoint, str):
            raise LoginFlowError("Nextcloud Login Flow initialization returned invalid poll data")

        _require_same_origin(login, base)
        _require_same_origin(poll_endpoint, base)
        self.target_policy.validate_url(login)
        self.target_policy.validate_url(poll_endpoint)

        return LoginFlowChallenge(
            requested_base_url=AnyHttpUrl(base),
            login_url=AnyHttpUrl(login),
            poll_endpoint=AnyHttpUrl(poll_endpoint),
            poll_token=SecretStr(token),
            expires_at=datetime.now(UTC) + _LOGIN_FLOW_TTL,
        )

    def poll(self, challenge: LoginFlowChallenge) -> LoginFlowCredentials | None:
        if datetime.now(UTC) >= challenge.expires_at:
            raise LoginFlowError("Nextcloud Login Flow has expired")

        poll_endpoint = str(challenge.poll_endpoint)
        expected_base = str(challenge.requested_base_url)
        _require_same_origin(poll_endpoint, expected_base)
        self.target_policy.validate_url(poll_endpoint)

        with self.client.stream(
            "POST",
            poll_endpoint,
            data={"token": challenge.poll_token.get_secret_value()},
        ) as response:
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                raise LoginFlowError(
                    f"Nextcloud Login Flow polling returned HTTP {response.status_code}"
                )
            payload = _read_bounded_json(response)

        server = payload.get("server")
        login_name = payload.get("loginName")
        app_password = payload.get("appPassword")
        if not all(isinstance(value, str) and value for value in (server, login_name, app_password)):
            raise LoginFlowError("Nextcloud Login Flow completion returned invalid credentials")

        server = _validate_base_url(server, allow_insecure_http=self.allow_insecure_http)
        _require_same_origin(server, expected_base)
        self.target_policy.validate_url(server)

        return LoginFlowCredentials(
            server=AnyHttpUrl(server),
            login_name=login_name,
            app_password=SecretStr(app_password),
        )

