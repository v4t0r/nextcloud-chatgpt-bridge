from __future__ import annotations

import json

import httpx
import pytest

from nextcloud_chatgpt_bridge.connections.login_flow import LoginFlowClient, LoginFlowError


BASE = "https://cloud.example.com/nextcloud"


def test_login_flow_v2_initiate_and_poll_never_exposes_password_in_start_result():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if str(request.url) == f"{BASE}/index.php/login/v2":
            return httpx.Response(
                200,
                json={
                    "poll": {
                        "token": "poll-secret",
                        "endpoint": "https://cloud.example.com/nextcloud/login/v2/poll",
                    },
                    "login": "https://cloud.example.com/nextcloud/login/v2/flow/abc",
                },
                request=request,
            )
        assert request.content == b"token=poll-secret"
        return httpx.Response(
            200,
            json={
                "server": BASE,
                "loginName": "bridge-user",
                "appPassword": "generated-app-password",
            },
            request=request,
        )

    with LoginFlowClient(transport=httpx.MockTransport(handler)) as client:
        challenge = client.initiate(BASE)
        assert "poll-secret" not in repr(challenge.poll_token)
        credentials = client.poll(challenge)

    assert credentials is not None
    assert credentials.login_name == "bridge-user"
    assert credentials.app_password.get_secret_value() == "generated-app-password"
    assert "generated-app-password" not in repr(credentials.app_password)
    assert calls == [
        f"{BASE}/index.php/login/v2",
        "https://cloud.example.com/nextcloud/login/v2/poll",
    ]


def test_poll_returns_none_while_user_has_not_completed_login():
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/index.php/login/v2"):
            return httpx.Response(
                200,
                json={
                    "poll": {
                        "token": "poll-secret",
                        "endpoint": "https://cloud.example.com/login/v2/poll",
                    },
                    "login": "https://cloud.example.com/login/v2/flow/abc",
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    with LoginFlowClient(transport=httpx.MockTransport(handler)) as client:
        challenge = client.initiate("https://cloud.example.com")
        assert client.poll(challenge) is None


def test_initiate_rejects_cross_origin_poll_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "poll": {
                    "token": "poll-secret",
                    "endpoint": "https://attacker.example/poll",
                },
                "login": "https://cloud.example.com/login/v2/flow/abc",
            },
            request=request,
        )

    with LoginFlowClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LoginFlowError, match="cross-origin"):
            client.initiate("https://cloud.example.com")


def test_poll_rejects_cross_origin_server_in_completion_response():
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/index.php/login/v2"):
            return httpx.Response(
                200,
                json={
                    "poll": {
                        "token": "poll-secret",
                        "endpoint": "https://cloud.example.com/login/v2/poll",
                    },
                    "login": "https://cloud.example.com/login/v2/flow/abc",
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "server": "https://attacker.example",
                "loginName": "user",
                "appPassword": "secret",
            },
            request=request,
        )

    with LoginFlowClient(transport=httpx.MockTransport(handler)) as client:
        challenge = client.initiate("https://cloud.example.com")
        with pytest.raises(LoginFlowError, match="cross-origin"):
            client.poll(challenge)


def test_login_flow_rejects_oversized_response_before_json_parse():
    oversized = json.dumps({"padding": "x" * (128 * 1024)}).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=oversized, request=request)

    with LoginFlowClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LoginFlowError, match="safety limit"):
            client.initiate("https://cloud.example.com")


def test_https_is_required_by_default():
    with LoginFlowClient(transport=httpx.MockTransport(lambda request: httpx.Response(500))) as client:
        with pytest.raises(LoginFlowError, match="HTTPS"):
            client.initiate("http://cloud.example.com")
