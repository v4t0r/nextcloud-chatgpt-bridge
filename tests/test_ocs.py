import httpx
import pytest

from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.providers.ocs import OCSClient, OCSError


def settings() -> Settings:
    return Settings(
        NEXTCLOUD_BASE_URL="https://cloud.example.com",
        NEXTCLOUD_USERNAME="bridge-user",
        NEXTCLOUD_APP_PASSWORD="test-app-password",  # noqa: S106
        NEXTCLOUD_ROOT_PATH="/ChatGPT",
        NEXTCLOUD_VERIFY_TLS=True,
    )


def test_get_capabilities_uses_authenticated_json_ocs_request():
    payload = {
        "ocs": {
            "meta": {"status": "ok", "statuscode": 100, "message": "OK"},
            "data": {
                "version": {"major": 34, "minor": 0, "micro": 1, "string": "34.0.1"},
                "capabilities": {"files_sharing": {"api_enabled": True}},
            },
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://cloud.example.com/ocs/v1.php/cloud/capabilities"
        assert request.headers["OCS-APIRequest"] == "true"
        assert "application/json" in request.headers["Accept"]
        assert request.headers["Authorization"].startswith("Basic ")
        return httpx.Response(200, json=payload, request=request)

    with OCSClient(settings(), transport=httpx.MockTransport(handler)) as client:
        data = client.get_capabilities()

    assert data["version"]["string"] == "34.0.1"
    assert "files_sharing" in data["capabilities"]


def test_ocs_error_never_echoes_remote_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="sensitive remote body", request=request)

    with OCSClient(settings(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(OCSError) as exc_info:
            client.get_capabilities()

    assert "HTTP 500" in str(exc_info.value)
    assert "sensitive remote body" not in str(exc_info.value)
