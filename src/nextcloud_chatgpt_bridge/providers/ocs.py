from __future__ import annotations

import json
from typing import Any

import httpx

from nextcloud_chatgpt_bridge.config import Settings

_MAX_OCS_RESPONSE_BYTES = 1024 * 1024


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

    def __enter__(self) -> "OCSClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def get_capabilities(self) -> dict[str, Any]:
        with self.client.stream("GET", f"{self.base_url}/ocs/v1.php/cloud/capabilities") as response:
            if response.status_code != 200:
                raise OCSError(
                    f"Nextcloud OCS capabilities returned HTTP {response.status_code}"
                )
            payload = _read_bounded_json(response)

        if not isinstance(payload.get("ocs"), dict):
            raise OCSError("Nextcloud OCS capabilities returned an unexpected response shape")

        ocs = payload["ocs"]
        meta = ocs.get("meta")
        data = ocs.get("data")
        if not isinstance(meta, dict) or not isinstance(data, dict):
            raise OCSError("Nextcloud OCS capabilities response is missing meta/data")

        status = str(meta.get("status", "")).lower()
        status_code = meta.get("statuscode")
        if status != "ok" and status_code != 100:
            raise OCSError("Nextcloud OCS capabilities request was not successful")

        return data

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
