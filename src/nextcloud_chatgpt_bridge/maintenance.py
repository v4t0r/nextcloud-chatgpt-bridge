from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, exists, select
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
        expired_refs = {row.poll_token_ref for row in expired_rows}
        expired_flow_ids = {row.flow_id for row in expired_rows}

        if expired_flow_ids:
            session.execute(
                delete(PendingLoginRow).where(PendingLoginRow.flow_id.in_(expired_flow_ids))
            )
        if expired_refs:
            session.execute(delete(SecretRow).where(SecretRow.secret_ref.in_(expired_refs)))

        pending_reference = exists(
            select(1).where(PendingLoginRow.poll_token_ref == SecretRow.secret_ref)
        )
        connection_reference = exists(
            select(1).where(ConnectionRow.credential_ref == SecretRow.secret_ref)
        )
        orphan_refs = set(
            session.scalars(
                select(SecretRow.secret_ref).where(
                    SecretRow.created_at < cutoff,
                    ~pending_reference,
                    ~connection_reference,
                )
            ).all()
        )
        # Expired poll secrets were intentionally removed above and should not be counted twice.
        true_orphan_refs = orphan_refs - expired_refs
        if true_orphan_refs:
            session.execute(
                delete(SecretRow).where(SecretRow.secret_ref.in_(true_orphan_refs))
            )

        session.commit()
        return CleanupReport(
            expired_pending_flows=len(expired_flow_ids),
            expired_poll_secrets=len(expired_refs),
            orphan_secrets=len(true_orphan_refs),
        )
