from __future__ import annotations

from typing import Any

import httpx

from nextcloud_chatgpt_bridge.config import Settings


class OCSError(RuntimeError):
    pass


class OCSClient:
    """Minimal read-only client for Nextcloud's OCS capabilities API."""

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
        response = self.client.get(f"{self.base_url}/ocs/v1.php/cloud/capabilities")
        if response.status_code != 200:
            raise OCSError(f"Nextcloud OCS capabilities returned HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise OCSError("Nextcloud OCS capabilities did not return valid JSON") from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("ocs"), dict):
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
