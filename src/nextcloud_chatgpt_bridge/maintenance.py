from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, exists, select, tuple_
from sqlalchemy.orm import Session, sessionmaker

from nextcloud_chatgpt_bridge.persistence import ConnectionRow, PendingLoginRow, SecretRow


@dataclass(slots=True, frozen=True)
class CleanupReport:
    expired_pending_flows: int
    expired_poll_secrets: int
    orphan_secrets: int


def cleanup_hosted_storage(
    session_factory: sessionmaker[Session],
    *,
    now: datetime | None = None,
    orphan_grace: timedelta = timedelta(hours=1),
) -> CleanupReport:
    """Delete expired login flows and sufficiently old unreferenced encrypted secrets.

    The grace period protects the normal small transaction window where a secret is inserted just
    before its connection/pending metadata record is committed.
    """
    current = now or datetime.now(UTC)
    cutoff = current - orphan_grace

    with session_factory() as session:
        expired_rows = session.scalars(
            select(PendingLoginRow).where(PendingLoginRow.expires_at < current)
        ).all()
        expired_keys = {(row.tenant_id, row.poll_token_ref) for row in expired_rows}
        expired_flow_ids = {row.flow_id for row in expired_rows}

        if expired_flow_ids:
            session.execute(
                delete(PendingLoginRow).where(PendingLoginRow.flow_id.in_(expired_flow_ids))
            )
        if expired_keys:
            session.execute(
                delete(SecretRow).where(
                    tuple_(SecretRow.tenant_id, SecretRow.secret_ref).in_(expired_keys)
                )
            )

        pending_reference = exists(
            select(1).where(
                PendingLoginRow.tenant_id == SecretRow.tenant_id,
                PendingLoginRow.poll_token_ref == SecretRow.secret_ref,
            )
        )
        connection_reference = exists(
            select(1).where(
                ConnectionRow.tenant_id == SecretRow.tenant_id,
                ConnectionRow.credential_ref == SecretRow.secret_ref,
            )
        )
        orphan_keys = {
            (tenant_id, secret_ref)
            for tenant_id, secret_ref in session.execute(
                select(SecretRow.tenant_id, SecretRow.secret_ref).where(
                    SecretRow.created_at < cutoff,
                    ~pending_reference,
                    ~connection_reference,
                )
            ).all()
        }
        # Expired poll secrets were intentionally removed above and should not be counted twice.
        true_orphan_keys = orphan_keys - expired_keys
        if true_orphan_keys:
            session.execute(
                delete(SecretRow).where(
                    tuple_(SecretRow.tenant_id, SecretRow.secret_ref).in_(true_orphan_keys)
                )
            )

        session.commit()
        return CleanupReport(
            expired_pending_flows=len(expired_flow_ids),
            expired_poll_secrets=len(expired_keys),
            orphan_secrets=len(true_orphan_keys),
        )
