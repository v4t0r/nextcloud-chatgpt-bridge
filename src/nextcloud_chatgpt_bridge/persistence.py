from __future__ import annotations

import base64
import binascii
import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from secrets import token_urlsafe

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    LargeBinary,
    String,
    Text,
    create_engine,
    delete,
    select,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from nextcloud_chatgpt_bridge.connections.models import ConnectionRecord, PendingLoginRecord

_SECRET_AAD_VERSION = b"nextcloud-chatgpt-bridge-secret-v1"
_MAX_SECRET_BYTES = 16 * 1024
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class PersistenceError(RuntimeError):
    pass


class CredentialStoreError(PersistenceError):
    pass


class Base(DeclarativeBase):
    pass


class PendingLoginRow(Base):
    __tablename__ = "pending_nextcloud_logins"

    flow_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(256), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    requested_base_url: Mapped[str] = mapped_column(Text, nullable=False)
    login_url: Mapped[str] = mapped_column(Text, nullable=False)
    poll_endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    poll_token_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_pending_login_tenant", "tenant_id"),)


class ConnectionRow(Base):
    __tablename__ = "nextcloud_connections"

    connection_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(256), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    login_name: Mapped[str] = mapped_column(String(512), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    credential_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    verify_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_nextcloud_connection_tenant", "tenant_id"),)


class SecretRow(Base):
    __tablename__ = "bridge_secrets"

    secret_ref: Mapped[str] = mapped_column(String(256), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(256), nullable=False)
    key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_bridge_secret_tenant", "tenant_id"),)


class HostedStorageConfig(BaseSettings):
    """Hosted persistence configuration. All secret-bearing values are redacted by Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: SecretStr = Field(alias="BRIDGE_DATABASE_URL")
    secret_active_key_id: str = Field(
        default="primary",
        min_length=1,
        max_length=64,
        alias="BRIDGE_SECRET_ACTIVE_KEY_ID",
    )
    secret_keys_json: SecretStr = Field(alias="BRIDGE_SECRET_KEYS_JSON")

    @model_validator(mode="after")
    def validate_hosted_storage(self) -> HostedStorageConfig:
        if not _KEY_ID_RE.fullmatch(self.secret_active_key_id):
            raise ValueError("BRIDGE_SECRET_ACTIVE_KEY_ID contains unsupported characters")
        try:
            url = make_url(self.database_url.get_secret_value())
        except Exception as exc:
            raise ValueError("BRIDGE_DATABASE_URL is not a valid SQLAlchemy URL") from exc
        if not url.drivername.startswith("postgresql"):
            raise ValueError("Hosted storage requires PostgreSQL")
        return self


@dataclass(slots=True, frozen=True)
class AesGcmKeyring:
    active_key_id: str
    keys: Mapping[str, bytes]

    def __post_init__(self) -> None:
        if not _KEY_ID_RE.fullmatch(self.active_key_id):
            raise ValueError("Invalid active encryption key id")
        normalized = dict(self.keys)
        if self.active_key_id not in normalized:
            raise ValueError("Active encryption key is missing from the keyring")
        if not normalized or len(normalized) > 16:
            raise ValueError("Secret keyring must contain between 1 and 16 keys")
        for key_id, key in normalized.items():
            if not _KEY_ID_RE.fullmatch(key_id):
                raise ValueError("Invalid encryption key id")
            if len(key) != 32:
                raise ValueError("AES-GCM secret keys must be exactly 32 bytes")
        object.__setattr__(self, "keys", normalized)

    @classmethod
    def from_json(cls, active_key_id: str, encoded_json: SecretStr) -> AesGcmKeyring:
        try:
            raw = json.loads(encoded_json.get_secret_value())
        except json.JSONDecodeError as exc:
            raise ValueError("BRIDGE_SECRET_KEYS_JSON is not valid JSON") from exc
        if not isinstance(raw, dict):
            raise ValueError("BRIDGE_SECRET_KEYS_JSON must be a JSON object")

        decoded: dict[str, bytes] = {}
        for key_id, encoded in raw.items():
            if not isinstance(key_id, str) or not isinstance(encoded, str):
                raise ValueError("Secret keyring entries must map string key IDs to base64 strings")
            try:
                decoded[key_id] = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Secret keyring contains invalid base64") from exc
        return cls(active_key_id=active_key_id, keys=decoded)


class DatabaseConnectionStore:
    """SQLAlchemy connection metadata store with tenant predicates in every read/delete query."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def put_pending(self, record: PendingLoginRecord) -> None:
        with self.session_factory() as session:
            existing = session.get(PendingLoginRow, record.flow_id)
            if existing is not None and existing.tenant_id != record.tenant_id:
                raise PersistenceError("Pending flow ID collision")
            row = existing or PendingLoginRow(flow_id=record.flow_id)
            row.tenant_id = record.tenant_id
            row.root_path = record.root_path
            row.requested_base_url = str(record.requested_base_url)
            row.login_url = str(record.login_url)
            row.poll_endpoint = str(record.poll_endpoint)
            row.poll_token_ref = record.poll_token_ref
            row.expires_at = record.expires_at
            row.created_at = record.created_at
            if existing is None:
                session.add(row)
            session.commit()

    def get_pending(self, flow_id: str, tenant_id: str) -> PendingLoginRecord | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(PendingLoginRow).where(
                    PendingLoginRow.flow_id == flow_id,
                    PendingLoginRow.tenant_id == tenant_id,
                )
            )
            return self._pending_record(row) if row is not None else None

    def delete_pending(self, flow_id: str, tenant_id: str) -> None:
        with self.session_factory() as session:
            session.execute(
                delete(PendingLoginRow).where(
                    PendingLoginRow.flow_id == flow_id,
                    PendingLoginRow.tenant_id == tenant_id,
                )
            )
            session.commit()

    def put_connection(self, record: ConnectionRecord) -> None:
        with self.session_factory() as session:
            existing = session.get(ConnectionRow, record.connection_id)
            if existing is not None and existing.tenant_id != record.tenant_id:
                raise PersistenceError("Connection ID collision")
            row = existing or ConnectionRow(connection_id=record.connection_id)
            row.tenant_id = record.tenant_id
            row.base_url = str(record.base_url)
            row.login_name = record.login_name
            row.root_path = record.root_path
            row.credential_ref = record.credential_ref
            row.verify_tls = record.verify_tls
            row.created_at = record.created_at
            if existing is None:
                session.add(row)
            session.commit()

    def get_connection(self, connection_id: str, tenant_id: str) -> ConnectionRecord | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(ConnectionRow).where(
                    ConnectionRow.connection_id == connection_id,
                    ConnectionRow.tenant_id == tenant_id,
                )
            )
            return self._connection_record(row) if row is not None else None

    def list_connections(self, tenant_id: str) -> Iterable[ConnectionRecord]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(ConnectionRow)
                .where(ConnectionRow.tenant_id == tenant_id)
                .order_by(ConnectionRow.created_at.asc(), ConnectionRow.connection_id.asc())
            ).all()
            return tuple(self._connection_record(row) for row in rows)

    def delete_connection(self, connection_id: str, tenant_id: str) -> None:
        with self.session_factory() as session:
            session.execute(
                delete(ConnectionRow).where(
                    ConnectionRow.connection_id == connection_id,
                    ConnectionRow.tenant_id == tenant_id,
                )
            )
            session.commit()

    @staticmethod
    def _pending_record(row: PendingLoginRow) -> PendingLoginRecord:
        return PendingLoginRecord(
            flow_id=row.flow_id,
            tenant_id=row.tenant_id,
            root_path=row.root_path,
            requested_base_url=row.requested_base_url,
            login_url=row.login_url,
            poll_endpoint=row.poll_endpoint,
            poll_token_ref=row.poll_token_ref,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )

    @staticmethod
    def _connection_record(row: ConnectionRow) -> ConnectionRecord:
        return ConnectionRecord(
            connection_id=row.connection_id,
            tenant_id=row.tenant_id,
            base_url=row.base_url,
            login_name=row.login_name,
            root_path=row.root_path,
            credential_ref=row.credential_ref,
            verify_tls=row.verify_tls,
            created_at=row.created_at,
        )


class EncryptedDatabaseCredentialStore:
    """Tenant-bound AES-256-GCM credential store backed by SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker[Session], keyring: AesGcmKeyring) -> None:
        self.session_factory = session_factory
        self.keyring = keyring

    def put(self, tenant_id: str, secret: SecretStr) -> str:
        plaintext = secret.get_secret_value().encode("utf-8")
        if not plaintext or len(plaintext) > _MAX_SECRET_BYTES:
            raise CredentialStoreError("Secret size is outside the allowed range")

        secret_ref = f"sec_{token_urlsafe(32)}"
        key_id = self.keyring.active_key_id
        key = self.keyring.keys[key_id]
        nonce = os.urandom(12)
        aad = self._aad(tenant_id, secret_ref, key_id)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)

        with self.session_factory() as session:
            session.add(
                SecretRow(
                    secret_ref=secret_ref,
                    tenant_id=tenant_id,
                    key_id=key_id,
                    nonce=nonce,
                    ciphertext=ciphertext,
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()
        return secret_ref

    def get(self, tenant_id: str, secret_ref: str) -> SecretStr | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(SecretRow).where(
                    SecretRow.secret_ref == secret_ref,
                    SecretRow.tenant_id == tenant_id,
                )
            )
            if row is None:
                return None
            key = self.keyring.keys.get(row.key_id)
            if key is None:
                raise CredentialStoreError("Encryption key for stored secret is unavailable")
            if len(row.nonce) != 12:
                raise CredentialStoreError("Stored secret has invalid encryption metadata")
            try:
                plaintext = AESGCM(key).decrypt(
                    row.nonce,
                    row.ciphertext,
                    self._aad(row.tenant_id, row.secret_ref, row.key_id),
                )
                value = plaintext.decode("utf-8")
            except (InvalidTag, UnicodeError) as exc:
                raise CredentialStoreError(
                    "Stored secret failed authenticated decryption"
                ) from exc
            return SecretStr(value)

    def delete(self, tenant_id: str, secret_ref: str) -> None:
        with self.session_factory() as session:
            session.execute(
                delete(SecretRow).where(
                    SecretRow.secret_ref == secret_ref,
                    SecretRow.tenant_id == tenant_id,
                )
            )
            session.commit()

    @staticmethod
    def _aad(tenant_id: str, secret_ref: str, key_id: str) -> bytes:
        return b"|".join(
            (
                _SECRET_AAD_VERSION,
                tenant_id.encode("ascii"),
                secret_ref.encode("ascii"),
                key_id.encode("ascii"),
            )
        )


def create_hosted_engine(config: HostedStorageConfig) -> Engine:
    """Create production PostgreSQL engine. Schema migrations are managed separately."""
    return create_engine(
        config.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
    )


def build_hosted_stores(
    config: HostedStorageConfig,
) -> tuple[Engine, DatabaseConnectionStore, EncryptedDatabaseCredentialStore]:
    engine = create_hosted_engine(config)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    keyring = AesGcmKeyring.from_json(
        config.secret_active_key_id,
        config.secret_keys_json,
    )
    return (
        engine,
        DatabaseConnectionStore(sessions),
        EncryptedDatabaseCredentialStore(sessions, keyring),
    )
