from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nextcloud_chatgpt_bridge.connections.models import ConnectionRecord, PendingLoginRecord
from nextcloud_chatgpt_bridge.maintenance import cleanup_hosted_storage
from nextcloud_chatgpt_bridge.persistence import (
    AesGcmKeyring,
    Base,
    DatabaseConnectionStore,
    EncryptedDatabaseSecretStore,
    SecretRow,
)


def make_stores():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    metadata = DatabaseConnectionStore(sessions)
    secrets = EncryptedDatabaseSecretStore(
        sessions,
        AesGcmKeyring(active_key_id="key-1", keys={"key-1": b"1" * 32}),
    )
    return sessions, metadata, secrets


def test_cleanup_removes_expired_poll_and_old_orphan_but_keeps_referenced_and_fresh():
    sessions, metadata, secrets = make_stores()
    now = datetime.now(UTC)

    expired_poll_ref = secrets.put(SecretStr("expired-poll"))
    metadata.put_pending(
        PendingLoginRecord(
            flow_id="flow_expired_1234567890",
            owner_subject="user-a",
            root_path="/ChatGPT",
            requested_base_url="https://cloud.example.com",
            login_url="https://cloud.example.com/login/v2/flow/old",
            poll_endpoint="https://cloud.example.com/login/v2/poll",
            poll_token_ref=expired_poll_ref,
            expires_at=now - timedelta(minutes=1),
            created_at=now - timedelta(hours=2),
        )
    )

    referenced_ref = secrets.put(SecretStr("live-app-password"))
    metadata.put_connection(
        ConnectionRecord(
            connection_id="nc_live_1234567890123456",
            owner_subject="user-a",
            base_url="https://cloud.example.com",
            login_name="bridge-user",
            root_path="/ChatGPT",
            credential_ref=referenced_ref,
            created_at=now - timedelta(hours=2),
        )
    )

    orphan_ref = secrets.put(SecretStr("orphan"))
    fresh_orphan_ref = secrets.put(SecretStr("fresh-orphan"))
    with sessions() as session:
        for secret_ref in (referenced_ref, orphan_ref):
            row = session.get(SecretRow, secret_ref)
            assert row is not None
            row.created_at = now - timedelta(hours=2)
        session.commit()

    report = cleanup_hosted_storage(
        sessions,
        now=now,
        orphan_grace=timedelta(hours=1),
    )

    assert report.expired_pending_flows == 1
    assert report.expired_poll_secrets == 1
    assert report.orphan_secrets == 1
    assert metadata.get_pending("flow_expired_1234567890", "user-a") is None
    assert secrets.get(expired_poll_ref) is None
    assert secrets.get(orphan_ref) is None
    assert secrets.get(referenced_ref).get_secret_value() == "live-app-password"  # type: ignore[union-attr]
    assert secrets.get(fresh_orphan_ref).get_secret_value() == "fresh-orphan"  # type: ignore[union-attr]
