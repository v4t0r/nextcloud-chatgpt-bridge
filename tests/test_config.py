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
