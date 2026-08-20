from nextcloud_chatgpt_bridge.capabilities import build_capability_report
from nextcloud_chatgpt_bridge.config import Settings


def settings() -> Settings:
    return Settings(
        NEXTCLOUD_BASE_URL="https://cloud.example.com",
        NEXTCLOUD_USERNAME="bridge-user",
        NEXTCLOUD_APP_PASSWORD="test-app-password",  # noqa: S106
        NEXTCLOUD_ROOT_PATH="/ChatGPT",
        NEXTCLOUD_VERIFY_TLS=True,
    )


def test_capability_report_detects_native_nextcloud_hints():
    data = {
        "version": {"major": 34, "minor": "0", "micro": 1, "string": "34.0.1"},
        "capabilities": {
            "files_sharing": {"api_enabled": True},
            "app_api": {"enabled": True},
            "assistant": {"features": ["context_agent"]},
        },
    }

    report = build_capability_report(settings(), data)

    assert report.nextcloud_version == "34.0.1"
    assert report.version_major == 34
    assert report.version_minor == 0
    assert report.version_micro == 1
    assert report.app_api_hint is True
    assert report.assistant_hint is True
    assert report.context_agent_hint is True
    assert report.context_agent_mcp_url == (
        "https://cloud.example.com/index.php/apps/app_api/proxy/context_agent/mcp/"
    )
    assert report.capability_groups == ["app_api", "assistant", "files_sharing"]
