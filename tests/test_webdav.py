import httpx
import pytest

from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.providers.webdav import WebDAVClient


MULTISTATUS = b'''<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
  <d:response>
    <d:href>/remote.php/dav/files/bridge-user/ChatGPT/</d:href>
    <d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype><oc:size>42</oc:size></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/bridge-user/ChatGPT/report.txt</d:href>
    <d:propstat><d:prop><d:resourcetype/><d:getcontentlength>42</d:getcontentlength><d:getcontenttype>text/plain</d:getcontenttype><d:getetag>&quot;abc&quot;</d:getetag></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
</d:multistatus>'''


def settings() -> Settings:
    return Settings(
        NEXTCLOUD_BASE_URL="https://cloud.example.com",
        NEXTCLOUD_USERNAME="bridge-user",
        NEXTCLOUD_APP_PASSWORD="test-app-password",  # noqa: S106
        NEXTCLOUD_ROOT_PATH="/ChatGPT",
        NEXTCLOUD_VERIFY_TLS=True,
    )


def test_list_files_returns_children_only():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PROPFIND"
        assert request.headers["Depth"] == "1"
        assert str(request.url) == "https://cloud.example.com/remote.php/dav/files/bridge-user/ChatGPT"
        return httpx.Response(207, content=MULTISTATUS, request=request)

    with WebDAVClient(settings(), transport=httpx.MockTransport(handler)) as client:
        items = client.list_files()

    assert len(items) == 1
    assert items[0].path == "report.txt"
    assert items[0].name == "report.txt"
    assert items[0].size == 42
    assert not items[0].is_dir


def test_parent_traversal_is_rejected_before_request():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network request must not occur")

    with WebDAVClient(settings(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError):
            client.download_file("../outside.txt")


def test_delete_root_is_refused_before_request():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network request must not occur")

    with WebDAVClient(settings(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError):
            client.delete("")
