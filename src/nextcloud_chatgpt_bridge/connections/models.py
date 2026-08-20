from __future__ import annotations

from datetime import UTC, datetime

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr


class LoginFlowChallenge(BaseModel):
    """Internal Nextcloud Login Flow v2 challenge. Never expose the poll token to clients."""

    requested_base_url: AnyHttpUrl
    login_url: AnyHttpUrl
    poll_endpoint: AnyHttpUrl
    poll_token: SecretStr
    expires_at: datetime


class LoginFlowCredentials(BaseModel):
    """Credentials returned once by Nextcloud Login Flow v2."""

    server: AnyHttpUrl
    login_name: str = Field(min_length=1, max_length=512)
    app_password: SecretStr


class PendingLoginRecord(BaseModel):
    flow_id: str = Field(min_length=16, max_length=256)
    owner_subject: str = Field(min_length=1, max_length=512)
    root_path: str = Field(default="/ChatGPT", min_length=2, max_length=4096)
    challenge: LoginFlowChallenge
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConnectionRecord(BaseModel):
    connection_id: str = Field(min_length=16, max_length=256)
    owner_subject: str = Field(min_length=1, max_length=512)
    base_url: AnyHttpUrl
    login_name: str = Field(min_length=1, max_length=512)
    root_path: str = Field(default="/ChatGPT", min_length=2, max_length=4096)
    credential_ref: str = Field(min_length=8, max_length=512)
    verify_tls: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConnectStart(BaseModel):
    """Safe response returned to the UI after starting account linking."""

    flow_id: str
    login_url: AnyHttpUrl
    expires_at: datetime


class ConnectionSummary(BaseModel):
    """Credential-free connection metadata safe to return through MCP/UI."""

    connection_id: str
    base_url: AnyHttpUrl
    login_name: str
    root_path: str
    connected_at: datetime


class DisconnectResult(BaseModel):
    connection_id: str
    disconnected: bool = True
    remote_credential_revoked: bool
