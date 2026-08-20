from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from nextcloud_chatgpt_bridge.capabilities import CapabilityReport, build_capability_report
from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.models import NavigationAppInfo, SearchProviderInfo


class AppAccessLevel(StrEnum):
    READ_WRITE = "read_write"
    READ_ONLY = "read_only"
    DETECTED_ONLY = "detected_only"


class NextcloudAppAccess(BaseModel):
    app_id: str
    display_name: str
    access_level: AppAccessLevel
    provider: str
    operations: list[str]


class SearchProviderSummary(BaseModel):
    provider_id: str
    display_name: str


class AppAccessReport(BaseModel):
    nextcloud_version: str | None
    apps: list[NextcloudAppAccess]
    search_providers: list[SearchProviderSummary]
    warnings: list[str]


_PROVIDER_HINTS = {
    "calendar": "caldav",
    "contacts": "carddav",
    "files": "webdav",
    "files_sharing": "ocs",
    "notes": "ocs_or_app_api",
    "deck": "ocs_or_app_api",
    "tasks": "caldav",
    "spreed": "ocs_or_app_api",
    "talk": "ocs_or_app_api",
    "tables": "ocs_or_app_api",
    "collectives": "ocs_or_app_api",
}


def build_app_access_report(
    settings: Settings,
    capability_data: dict[str, object],
    *,
    navigation_apps: list[NavigationAppInfo],
    search_providers: list[SearchProviderInfo],
    warnings: list[str] | None = None,
) -> AppAccessReport:
    """Build a user-visible inventory without requiring Nextcloud administrator access."""
    capability_report: CapabilityReport = build_capability_report(settings, capability_data)
    by_id = {item.app_id: item for item in navigation_apps}
    by_id.setdefault("files", NavigationAppInfo(app_id="files", display_name="Files"))

    apps: list[NextcloudAppAccess] = []
    for app_id, item in sorted(by_id.items()):
        if app_id == "files":
            level = AppAccessLevel.READ_WRITE
            operations = ["list", "metadata", "read", "write", "move", "delete"]
        elif app_id == "files_sharing":
            level = AppAccessLevel.READ_ONLY
            operations = ["list_shares"]
        else:
            level = AppAccessLevel.DETECTED_ONLY
            operations = []
        apps.append(
            NextcloudAppAccess(
                app_id=app_id,
                display_name=item.display_name,
                access_level=level,
                provider=_PROVIDER_HINTS.get(app_id, "not_implemented"),
                operations=operations,
            )
        )

    providers = [
        SearchProviderSummary(
            provider_id=item.provider_id,
            display_name=item.display_name,
        )
        for item in sorted(search_providers, key=lambda value: value.provider_id)
    ]
    return AppAccessReport(
        nextcloud_version=capability_report.nextcloud_version,
        apps=apps,
        search_providers=providers,
        warnings=list(warnings or []),
    )
