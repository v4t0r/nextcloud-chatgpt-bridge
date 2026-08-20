from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.models import (
    NavigationAppInfo,
    SearchProviderInfo,
    SearchResultInfo,
    ShareInfo,
)

_MAX_OCS_RESPONSE_BYTES = 1024 * 1024
_MAX_OCS_ITEMS = 200
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class OCSError(RuntimeError):
    pass


def _read_bounded_json(response: httpx.Response) -> dict[str, Any]:
    data = bytearray()
    for chunk in response.iter_bytes():
        data.extend(chunk)
        if len(data) > _MAX_OCS_RESPONSE_BYTES:
            raise OCSError("Nextcloud OCS response exceeded the safety limit")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OCSError("Nextcloud OCS endpoint did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise OCSError("Nextcloud OCS endpoint returned an unexpected response shape")
    return payload


class OCSClient:
    """Bounded client for Nextcloud OCS discovery and credential lifecycle operations."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self.base_url = str(settings.nextcloud_base_url).rstrip("/")
        self.client = httpx.Client(
            auth=httpx.BasicAuth(
                settings.nextcloud_username,
                settings.nextcloud_app_password.get_secret_value(),
            ),
            verify=settings.nextcloud_verify_tls,
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,
            transport=transport,
            headers={
                "Accept": "application/json",
                "OCS-APIRequest": "true",
            },
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> OCSClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def get_capabilities(self) -> dict[str, Any]:
        data = self._get_ocs_data("/ocs/v1.php/cloud/capabilities", operation="capabilities")
        if not isinstance(data, dict):
            raise OCSError("Nextcloud OCS capabilities returned an unexpected response shape")
        return data

    def get_navigation_apps(self) -> list[NavigationAppInfo]:
        """List apps visible in the authenticated user's Nextcloud navigation."""
        data = self._get_ocs_data("/ocs/v2.php/core/navigation/apps", operation="navigation")
        if not isinstance(data, list):
            raise OCSError("Nextcloud OCS navigation returned an unexpected response shape")
        result: list[NavigationAppInfo] = []
        for item in data[:_MAX_OCS_ITEMS]:
            if not isinstance(item, dict):
                continue
            app_id = _safe_text(item.get("id"), 128)
            display_name = _safe_text(item.get("name"), 256)
            if app_id and _SAFE_IDENTIFIER.fullmatch(app_id) and display_name:
                result.append(NavigationAppInfo(app_id=app_id, display_name=display_name))
        return result

    def get_search_providers(self) -> list[SearchProviderInfo]:
        data = self._get_ocs_data("/ocs/v2.php/search/providers", operation="search providers")
        if not isinstance(data, list):
            raise OCSError("Nextcloud OCS search providers returned an unexpected response shape")
        result: list[SearchProviderInfo] = []
        for item in data[:_MAX_OCS_ITEMS]:
            if not isinstance(item, dict):
                continue
            provider_id = _safe_text(item.get("id"), 128)
            display_name = _safe_text(item.get("name"), 256)
            if provider_id and _SAFE_IDENTIFIER.fullmatch(provider_id) and display_name:
                result.append(
                    SearchProviderInfo(
                        provider_id=provider_id,
                        display_name=display_name,
                    )
                )
        return result

    def search(
        self,
        provider_id: str,
        term: str,
        *,
        limit: int = 20,
        cursor: int | None = None,
    ) -> tuple[list[SearchResultInfo], int | None]:
        provider = provider_id.strip()
        query = term.strip()
        if not _SAFE_IDENTIFIER.fullmatch(provider):
            raise ValueError("Search provider ID contains unsupported characters")
        if not query or len(query) > 256:
            raise ValueError("Search term must contain between 1 and 256 characters")
        if not 1 <= limit <= 50:
            raise ValueError("Search limit must be between 1 and 50")
        if cursor is not None and cursor < 0:
            raise ValueError("Search cursor must not be negative")

        params: dict[str, str | int] = {"term": query, "limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = self._get_ocs_data(
            f"/ocs/v2.php/search/providers/{quote(provider, safe='')}/search",
            operation="search",
            params=params,
        )
        if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
            raise OCSError("Nextcloud OCS search returned an unexpected response shape")

        results: list[SearchResultInfo] = []
        for item in data["entries"][:limit]:
            if not isinstance(item, dict):
                continue
            title = _safe_text(item.get("title"), 512)
            if not title:
                continue
            results.append(
                SearchResultInfo(
                    title=title,
                    subline=_safe_text(item.get("subline"), 512),
                    resource_path=self._same_origin_path(item.get("resourceUrl")),
                )
            )
        next_cursor = data.get("cursor")
        if isinstance(next_cursor, bool) or not isinstance(next_cursor, int):
            next_cursor = None
        return results, next_cursor

    def list_shares(
        self,
        *,
        path: str | None = None,
        include_subfiles: bool = False,
    ) -> list[ShareInfo]:
        params: dict[str, str] = {"reshares": "true"}
        if path is not None:
            normalized = path.strip()
            if not normalized or len(normalized) > 4096 or "\x00" in normalized:
                raise ValueError("Share path is invalid")
            params["path"] = normalized
            params["subfiles"] = "true" if include_subfiles else "false"
        data = self._get_ocs_data(
            "/ocs/v2.php/apps/files_sharing/api/v1/shares",
            operation="shares",
            params=params,
        )
        if not isinstance(data, list):
            raise OCSError("Nextcloud OCS shares returned an unexpected response shape")
        shares: list[ShareInfo] = []
        for item in data[:_MAX_OCS_ITEMS]:
            if not isinstance(item, dict):
                continue
            share_id = _safe_text(item.get("id"), 128)
            if not share_id:
                continue
            shares.append(
                ShareInfo(
                    share_id=share_id,
                    share_type=_safe_int(item.get("share_type")),
                    item_type=_safe_text(item.get("item_type"), 128),
                    path=_safe_text(item.get("path"), 4096),
                    permissions=_safe_int(item.get("permissions")),
                    shared_with=_safe_text(
                        item.get("share_with_displayname") or item.get("share_with"),
                        256,
                    ),
                    expiration=_safe_text(item.get("expiration"), 64),
                )
            )
        return shares

    def delete_app_password(self) -> None:
        """Revoke the app password currently authenticating this client."""
        with self.client.stream(
            "DELETE",
            f"{self.base_url}/ocs/v2.php/core/apppassword",
        ) as response:
            if response.status_code != 200:
                raise OCSError(
                    f"Nextcloud app-password revocation returned HTTP {response.status_code}"
                )

    def _get_ocs_data(
        self,
        endpoint: str,
        *,
        operation: str,
        params: dict[str, str | int] | None = None,
    ) -> Any:
        if not endpoint.startswith("/ocs/"):
            raise ValueError("OCS endpoint must be an absolute OCS path")
        with self.client.stream("GET", f"{self.base_url}{endpoint}", params=params) as response:
            if response.status_code != 200:
                raise OCSError(f"Nextcloud OCS {operation} returned HTTP {response.status_code}")
            payload = _read_bounded_json(response)
        if not isinstance(payload.get("ocs"), dict):
            raise OCSError(f"Nextcloud OCS {operation} returned an unexpected response shape")
        ocs = payload["ocs"]
        meta = ocs.get("meta")
        if not isinstance(meta, dict) or "data" not in ocs:
            raise OCSError(f"Nextcloud OCS {operation} response is missing meta/data")
        status = str(meta.get("status", "")).lower()
        status_code = meta.get("statuscode")
        if status != "ok" and status_code != 100:
            raise OCSError(f"Nextcloud OCS {operation} request was not successful")
        return ocs["data"]

    def _same_origin_path(self, value: object) -> str | None:
        text = _safe_text(value, 4096)
        if not text:
            return None
        parsed = urlsplit(text)
        if not parsed.scheme and not parsed.netloc:
            return parsed.path if parsed.path.startswith("/") else None
        expected = urlsplit(self.base_url)
        if (parsed.scheme, parsed.hostname, parsed.port) != (
            expected.scheme,
            expected.hostname,
            expected.port,
        ):
            return None
        return parsed.path or "/"


def _safe_text(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.replace("\x00", "").split())
    if not normalized:
        return None
    return normalized[:limit]


def _safe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None

