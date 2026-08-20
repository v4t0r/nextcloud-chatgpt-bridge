from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    nextcloud_base_url: AnyHttpUrl = Field(alias="NEXTCLOUD_BASE_URL")
    nextcloud_username: str = Field(alias="NEXTCLOUD_USERNAME", min_length=1)
    nextcloud_app_password: SecretStr = Field(alias="NEXTCLOUD_APP_PASSWORD")
    nextcloud_root_path: str = Field(default="/ChatGPT", alias="NEXTCLOUD_ROOT_PATH")
    nextcloud_verify_tls: bool = Field(default=True, alias="NEXTCLOUD_VERIFY_TLS")
    allow_insecure_http: bool = Field(default=False, alias="NEXTCLOUD_ALLOW_INSECURE_HTTP")
    max_transfer_bytes: int = Field(
        default=4_000_000,
        ge=1_024,
        le=25_000_000,
        alias="NEXTCLOUD_MAX_TRANSFER_BYTES",
    )

    @field_validator("nextcloud_root_path")
    @classmethod
    def validate_root_path(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            raise ValueError("NEXTCLOUD_ROOT_PATH must be an absolute Nextcloud path")

        normalized = str(PurePosixPath(value))
        if normalized in {"/", "."}:
            raise ValueError("Refusing to use the entire Nextcloud account as root path")
        if ".." in PurePosixPath(value).parts:
            raise ValueError("NEXTCLOUD_ROOT_PATH must not contain parent traversal")
        return normalized

    @model_validator(mode="after")
    def enforce_encrypted_transport(self) -> "Settings":
        if self.nextcloud_base_url.scheme != "https" and not self.allow_insecure_http:
            raise ValueError(
                "NEXTCLOUD_BASE_URL must use HTTPS unless NEXTCLOUD_ALLOW_INSECURE_HTTP=true"
            )
        return self
