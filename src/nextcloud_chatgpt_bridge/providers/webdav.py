from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit

import httpx
from defusedxml import ElementTree as ET

from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.models import FileInfo

DAV = "DAV:"
OC = "http://owncloud.org/ns"

_PROPFIND_BODY = """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
  <d:prop>
    <d:getlastmodified/>
    <d:getcontentlength/>
    <d:getcontenttype/>
    <d:resourcetype/>
    <d:getetag/>
    <oc:size/>
  </d:prop>
</d:propfind>
"""


class WebDAVError(RuntimeError):
    pass


class WebDAVClient:
    """Minimal Nextcloud WebDAV provider constrained to one configured root folder."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        base = str(settings.nextcloud_base_url).rstrip("/")
        user = quote(settings.nextcloud_username, safe="")
        root = self._encode_path(settings.nextcloud_root_path)
        self.base_url = f"{base}/remote.php/dav/files/{user}{root}"
        self.client = httpx.Client(
            auth=httpx.BasicAuth(
                settings.nextcloud_username,
                settings.nextcloud_app_password.get_secret_value(),
            ),
            verify=settings.nextcloud_verify_tls,
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,
            transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "WebDAVClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def _encode_path(path: str) -> str:
        parts = PurePosixPath(path).parts
        encoded = "/".join(quote(part, safe="") for part in parts if part not in {"/", ""})
        return f"/{encoded}" if encoded else ""

    @staticmethod
    def _normalize_relative(path: str) -> str:
        raw = path.strip().replace("\\", "/")
        if raw in {"", ".", "/"}:
            return ""
        candidate = PurePosixPath(raw.lstrip("/"))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("Path escapes the configured Nextcloud root")
        normalized = str(candidate)
        if normalized == ".":
            return ""
        return normalized

    def _url(self, relative_path: str = "") -> str:
        rel = self._normalize_relative(relative_path)
        return self.base_url if not rel else f"{self.base_url}/{self._encode_path(rel).lstrip('/')}"

    @staticmethod
    def _raise_for_status(response: httpx.Response, expected: set[int]) -> None:
        if response.status_code not in expected:
            # Never echo a remote response body into MCP errors. WebDAV bodies are untrusted data
            # and can contain sensitive server details or prompt-injection text.
            raise WebDAVError(f"Nextcloud WebDAV returned HTTP {response.status_code}")

    def list_files(self, path: str = "") -> list[FileInfo]:
        response = self.client.request(
            "PROPFIND",
            self._url(path),
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
            content=_PROPFIND_BODY,
        )
        self._raise_for_status(response, {207})
        entries = self._parse_multistatus(response.content)
        target = self._normalize_relative(path).rstrip("/")
        return [entry for entry in entries if entry.path.rstrip("/") != target]

    def stat(self, path: str) -> FileInfo:
        response = self.client.request(
            "PROPFIND",
            self._url(path),
            headers={"Depth": "0", "Content-Type": "application/xml; charset=utf-8"},
            content=_PROPFIND_BODY,
        )
        self._raise_for_status(response, {207})
        entries = self._parse_multistatus(response.content)
        if not entries:
            raise WebDAVError("Nextcloud returned no metadata for the requested path")
        return entries[0]

    def download_file(self, path: str, *, max_bytes: int | None = None) -> bytes:
        """Stream a file with a hard byte cap to avoid TOCTOU/unbounded-memory downloads."""
        limit = self.settings.max_transfer_bytes if max_bytes is None else max_bytes
        if limit < 1:
            raise ValueError("max_bytes must be positive")

        chunks: list[bytes] = []
        total = 0
        with self.client.stream("GET", self._url(path)) as response:
            self._raise_for_status(response, {200})

            content_length = response.headers.get("Content-Length")
            if content_length and content_length.isdigit() and int(content_length) > limit:
                raise WebDAVError("Nextcloud file exceeds the configured transfer limit")

            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > limit:
                    raise WebDAVError("Nextcloud file exceeds the configured transfer limit")
                chunks.append(chunk)

        return b"".join(chunks)

    def upload_file(self, path: str, content: bytes, *, overwrite: bool = False) -> FileInfo:
        if len(content) > self.settings.max_transfer_bytes:
            raise ValueError("Upload exceeds the configured transfer limit")
        headers = {"If-None-Match": "*"} if not overwrite else {}
        response = self.client.put(self._url(path), content=content, headers=headers)
        self._raise_for_status(response, {201, 204})
        return self.stat(path)

    def create_folder(self, path: str) -> FileInfo:
        response = self.client.request("MKCOL", self._url(path))
        self._raise_for_status(response, {201})
        return self.stat(path)

    def move(self, source: str, destination: str, *, overwrite: bool = False) -> FileInfo:
        response = self.client.request(
            "MOVE",
            self._url(source),
            headers={
                "Destination": self._url(destination),
                "Overwrite": "T" if overwrite else "F",
            },
        )
        self._raise_for_status(response, {201, 204})
        return self.stat(destination)

    def delete(self, path: str) -> None:
        if not self._normalize_relative(path):
            raise ValueError("Refusing to delete the configured Nextcloud root")
        response = self.client.delete(self._url(path))
        self._raise_for_status(response, {204})

    def _parse_multistatus(self, payload: bytes) -> list[FileInfo]:
        root = ET.fromstring(payload)
        result: list[FileInfo] = []
        base_path = urlsplit(self.base_url).path.rstrip("/")

        for response in root.findall(f"{{{DAV}}}response"):
            href = response.findtext(f"{{{DAV}}}href") or ""
            href_path = unquote(urlsplit(href).path).rstrip("/")
            if href_path != base_path and not href_path.startswith(f"{base_path}/"):
                continue
            rel = href_path[len(base_path) :].lstrip("/")

            prop = None
            for propstat in response.findall(f"{{{DAV}}}propstat"):
                status = propstat.findtext(f"{{{DAV}}}status") or ""
                if " 200 " in status:
                    prop = propstat.find(f"{{{DAV}}}prop")
                    break
            if prop is None:
                continue

            resource_type = prop.find(f"{{{DAV}}}resourcetype")
            is_dir = resource_type is not None and resource_type.find(f"{{{DAV}}}collection") is not None
            size_text = prop.findtext(f"{{{OC}}}size") or prop.findtext(f"{{{DAV}}}getcontentlength")

            result.append(
                FileInfo(
                    path=rel,
                    name=PurePosixPath(rel).name
                    if rel
                    else PurePosixPath(self.settings.nextcloud_root_path).name,
                    is_dir=is_dir,
                    size=int(size_text) if size_text and size_text.isdigit() else None,
                    content_type=prop.findtext(f"{{{DAV}}}getcontenttype"),
                    etag=prop.findtext(f"{{{DAV}}}getetag"),
                    last_modified=prop.findtext(f"{{{DAV}}}getlastmodified"),
                )
            )
        return result
