from nextcloud_chatgpt_bridge.app_access import AppAccessLevel, build_app_access_report
from nextcloud_chatgpt_bridge.config import Settings
from nextcloud_chatgpt_bridge.models import NavigationAppInfo, SearchProviderInfo


def settings() -> Settings:
    return Settings(
        NEXTCLOUD_BASE_URL="https://cloud.example.com",
        NEXTCLOUD_USERNAME="bridge-user",
        NEXTCLOUD_APP_PASSWORD="test-app-password",  # noqa: S106
        NEXTCLOUD_ROOT_PATH="/ChatGPT",
    )


def test_app_access_report_distinguishes_callable_and_detected_apps():
    report = build_app_access_report(
        settings(),
        {
            "version": {"string": "33.0.7"},
            "capabilities": {"files_sharing": {"api_enabled": True}},
        },
        navigation_apps=[
            NavigationAppInfo(app_id="calendar", display_name="Calendar"),
            NavigationAppInfo(app_id="notes", display_name="Notes"),
        ],
        search_providers=[
            SearchProviderInfo(provider_id="files", display_name="Files"),
        ],
    )

    apps = {app.app_id: app for app in report.apps}
    assert report.nextcloud_version == "33.0.7"
    assert apps["files"].access_level == AppAccessLevel.READ_WRITE
    assert apps["files"].provider == "webdav"
    assert apps["calendar"].access_level == AppAccessLevel.DETECTED_ONLY
    assert apps["calendar"].provider == "caldav"
    assert apps["notes"].provider == "ocs_or_app_api"
    assert report.search_providers[0].provider_id == "files"
