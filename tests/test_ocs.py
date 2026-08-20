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


def test_capabilities_response_is_bounded():
    oversized = b"{" + b" " * (1024 * 1024) + b"}"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=oversized, request=request)

    with OCSClient(settings(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(OCSError, match="safety limit"):
            client.get_capabilities()


def test_delete_app_password_uses_authenticated_ocs_endpoint():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.method)
        assert str(request.url) == "https://cloud.example.com/ocs/v2.php/core/apppassword"
        assert request.headers["OCS-APIRequest"] == "true"
        assert request.headers["Authorization"].startswith("Basic ")
        return httpx.Response(200, request=request)

    with OCSClient(settings(), transport=httpx.MockTransport(handler)) as client:
        client.delete_app_password()

    assert seen == ["DELETE"]


def test_user_app_search_and_share_metadata_are_sanitized():
    def ocs(data):
        return {
            "ocs": {
                "meta": {"status": "ok", "statuscode": 100, "message": "OK"},
                "data": data,
            }
        }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/ocs/v2.php/core/navigation/apps":
            return httpx.Response(
                200,
                json=ocs(
                    [
                        {"id": "files", "name": "Files\nInjected"},
                        {"id": "bad/id", "name": "Bad"},
                    ]
                ),
                request=request,
            )
        if path == "/ocs/v2.php/search/providers":
            return httpx.Response(
                200,
                json=ocs([{"id": "files", "name": "Files"}]),
                request=request,
            )
        if path == "/ocs/v2.php/search/providers/files/search":
            assert request.url.params["term"] == "invoice"
            return httpx.Response(
                200,
                json=ocs(
                    {
                        "entries": [
                            {
                                "title": "Invoice.pdf",
                                "subline": "Files",
                                "resourceUrl": "https://cloud.example.com/index.php/f/42?secret=x",
                            },
                            {
                                "title": "External",
                                "resourceUrl": "https://evil.example/file",
                            },
                        ],
                        "cursor": 4,
                    }
                ),
                request=request,
            )
        if path == "/ocs/v2.php/apps/files_sharing/api/v1/shares":
            return httpx.Response(
                200,
                json=ocs(
                    [
                        {
                            "id": "7",
                            "share_type": 0,
                            "item_type": "file",
                            "path": "/ChatGPT/invoice.pdf",
                            "permissions": 1,
                            "share_with_displayname": "Household Member",
                            "expiration": "2026-09-01 00:00:00",
                            "token": "must-not-leak",
                            "url": "https://cloud.example.com/s/token",
                        }
                    ]
                ),
                request=request,
            )
        raise AssertionError(path)

    with OCSClient(settings(), transport=httpx.MockTransport(handler)) as client:
        apps = client.get_navigation_apps()
        providers = client.get_search_providers()
        results, cursor = client.search("files", "invoice")
        shares = client.list_shares(path="/ChatGPT", include_subfiles=True)

    assert apps[0].app_id == "files"
    assert apps[0].display_name == "Files Injected"
    assert len(apps) == 1
    assert providers[0].provider_id == "files"
    assert results[0].resource_path == "/index.php/f/42"
    assert results[1].resource_path is None
    assert cursor == 4
    assert shares[0].path == "/ChatGPT/invoice.pdf"
    assert "must-not-leak" not in repr(shares[0])
