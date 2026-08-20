from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from nextcloud_chatgpt_bridge.connections.models import ConnectionRecord, PendingLoginRecord
from nextcloud_chatgpt_bridge.persistence import (
    AesGcmKeyring,
    Base,
    DatabaseConnectionStore,
    EncryptedDatabaseSecretStore,
    HostedStorageConfig,
    SecretRow,
    SecretStoreError,
)


def make_sessions() -> sessionmaker[Session]:
    # SQLite is deliberately used only as an isolated unit-test backend for SQLAlchemy mappings.
    # HostedStorageConfig itself refuses SQLite and production requires PostgreSQL.
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def keyring(active: str = "key-1", **extra: bytes) -> AesGcmKeyring:
    keys = {"key-1": b"1" * 32, **extra}
    return AesGcmKeyring(active_key_id=active, keys=keys)


def pending(owner: str = "user-a") -> PendingLoginRecord:
    return PendingLoginRecord(
        flow_id="flow_12345678901234567890",
        owner_subject=owner,
        root_path="/ChatGPT",
        requested_base_url="https://cloud.example.com",
        login_url="https://cloud.example.com/login/v2/flow/abc",
        poll_endpoint="https://cloud.example.com/login/v2/poll",
        poll_token_ref="sec_poll_1234567890",
        expires_at=datetime.now(UTC) + timedelta(minutes=20),
    )


def connection(owner: str = "user-a") -> ConnectionRecord:
    return ConnectionRecord(
        connection_id="nc_12345678901234567890",
        owner_subject=owner,
        base_url="https://cloud.example.com",
        login_name="bridge-user",
        root_path="/ChatGPT",
        credential_ref="sec_app_1234567890",
        verify_tls=True,
    )


def test_database_store_applies_owner_predicate_to_pending_and_connections():
    sessions = make_sessions()
    store = DatabaseConnectionStore(sessions)
    store.put_pending(pending())
    store.put_connection(connection())

    assert store.get_pending("flow_12345678901234567890", "user-a") is not None
    assert store.get_pending("flow_12345678901234567890", "user-b") is None
    assert store.get_connection("nc_12345678901234567890", "user-a") is not None
    assert store.get_connection("nc_12345678901234567890", "user-b") is None
    assert len(tuple(store.list_connections("user-a"))) == 1
    assert tuple(store.list_connections("user-b")) == ()

    store.delete_pending("flow_12345678901234567890", "user-b")
    store.delete_connection("nc_12345678901234567890", "user-b")
    assert store.get_pending("flow_12345678901234567890", "user-a") is not None
    assert store.get_connection("nc_12345678901234567890", "user-a") is not None


def test_database_store_refuses_id_collision_across_tenants():
    sessions = make_sessions()
    store = DatabaseConnectionStore(sessions)
    store.put_connection(connection("user-a"))

    with pytest.raises(RuntimeError, match="collision"):
        store.put_connection(connection("user-b"))


def test_encrypted_secret_store_never_persists_plaintext_and_round_trips():
    sessions = make_sessions()
    store = EncryptedDatabaseSecretStore(sessions, keyring())
    secret_value = "nextcloud-app-password-value"

    secret_ref = store.put(SecretStr(secret_value))

    with sessions() as session:
        row = session.get(SecretRow, secret_ref)
        assert row is not None
        assert secret_value.encode() not in row.ciphertext
        assert len(row.nonce) == 12
        assert row.key_id == "key-1"

    restored = store.get(secret_ref)
    assert restored is not None
    assert restored.get_secret_value() == secret_value


def test_encrypted_secret_store_detects_ciphertext_tampering():
    sessions = make_sessions()
    store = EncryptedDatabaseSecretStore(sessions, keyring())
    secret_ref = store.put(SecretStr("secret-value"))

    with sessions() as session:
        row = session.get(SecretRow, secret_ref)
        assert row is not None
        modified = bytearray(row.ciphertext)
        modified[-1] ^= 1
        row.ciphertext = bytes(modified)
        session.commit()

    with pytest.raises(SecretStoreError, match="authenticated decryption"):
        store.get(secret_ref)


def test_keyring_supports_reading_old_key_while_new_writes_use_active_key():
    sessions = make_sessions()
    old_store = EncryptedDatabaseSecretStore(sessions, keyring())
    old_ref = old_store.put(SecretStr("old-secret"))

    rotated = AesGcmKeyring(
        active_key_id="key-2",
        keys={"key-1": b"1" * 32, "key-2": b"2" * 32},
    )
    new_store = EncryptedDatabaseSecretStore(sessions, rotated)

    assert new_store.get(old_ref).get_secret_value() == "old-secret"  # type: ignore[union-attr]
    new_ref = new_store.put(SecretStr("new-secret"))
    with sessions() as session:
        row = session.get(SecretRow, new_ref)
        assert row is not None
        assert row.key_id == "key-2"


def test_hosted_storage_config_requires_postgres_and_redacts_secrets():
    encoded = base64.b64encode(b"k" * 32).decode()
    keys_json = '{"primary":"' + encoded + '"}'
    config = HostedStorageConfig(
        BRIDGE_DATABASE_URL="postgresql+psycopg://dbuser:dbpassword@db.example/bridge",
        BRIDGE_SECRET_ACTIVE_KEY_ID="primary",
        BRIDGE_SECRET_KEYS_JSON=keys_json,
    )

    representation = repr(config)
    assert "dbpassword" not in representation
    assert encoded not in representation
    parsed = AesGcmKeyring.from_json(config.secret_active_key_id, config.secret_keys_json)
    assert parsed.keys["primary"] == b"k" * 32

    with pytest.raises(ValidationError, match="PostgreSQL"):
        HostedStorageConfig(
            BRIDGE_DATABASE_URL="sqlite:///bridge.db",
            BRIDGE_SECRET_ACTIVE_KEY_ID="primary",
            BRIDGE_SECRET_KEYS_JSON=keys_json,
        )
