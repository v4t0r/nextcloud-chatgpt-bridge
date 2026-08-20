import pytest
from pydantic import ValidationError

from nextcloud_chatgpt_bridge.config import Settings


def make_settings(**overrides):
    values = {
        "NEXTCLOUD_BASE_URL": "https://cloud.example.com",
        "NEXTCLOUD_USERNAME": "bridge-user",
        "NEXTCLOUD_APP_PASSWORD": "secret-value",
        "NEXTCLOUD_ROOT_PATH": "/ChatGPT",
        "NEXTCLOUD_VERIFY_TLS": "true",
        "NEXTCLOUD_ALLOW_INSECURE_HTTP": "false",
        "NEXTCLOUD_MAX_TRANSFER_BYTES": 4_000_000,
    }
    values.update(overrides)
    return Settings(**values)


def test_root_path_is_normalized():
    settings = make_settings(NEXTCLOUD_ROOT_PATH="/ChatGPT/Projects/")
    assert settings.nextcloud_root_path == "/ChatGPT/Projects"


def test_root_path_rejects_parent_traversal():
    with pytest.raises(ValidationError):
        make_settings(NEXTCLOUD_ROOT_PATH="/ChatGPT/Projects/../Secrets")


def test_root_path_rejects_entire_account():
    with pytest.raises(ValidationError):
        make_settings(NEXTCLOUD_ROOT_PATH="/")


def test_password_is_secret_type():
    settings = make_settings()
    assert "secret-value" not in repr(settings.nextcloud_app_password)


def test_plain_http_is_rejected_by_default():
    with pytest.raises(ValidationError):
        make_settings(NEXTCLOUD_BASE_URL="http://cloud.example.com")


def test_plain_http_requires_explicit_development_override():
    settings = make_settings(
        NEXTCLOUD_BASE_URL="http://127.0.0.1:8080",
        NEXTCLOUD_ALLOW_INSECURE_HTTP="true",
    )
    assert settings.nextcloud_base_url.scheme == "http"


def test_transfer_limit_has_hard_upper_bound():
    with pytest.raises(ValidationError):
        make_settings(NEXTCLOUD_MAX_TRANSFER_BYTES=25_000_001)
