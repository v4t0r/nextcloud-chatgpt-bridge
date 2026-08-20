BEGIN;

CREATE TABLE bridge_secrets (
    secret_ref VARCHAR(256) PRIMARY KEY,
    key_id VARCHAR(64) NOT NULL,
    nonce BYTEA NOT NULL,
    ciphertext BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_bridge_secret_nonce_12 CHECK (octet_length(nonce) = 12),
    CONSTRAINT ck_bridge_secret_ciphertext_tag CHECK (octet_length(ciphertext) >= 16)
);

CREATE TABLE pending_nextcloud_logins (
    flow_id VARCHAR(256) PRIMARY KEY,
    owner_subject VARCHAR(512) NOT NULL,
    root_path TEXT NOT NULL,
    requested_base_url TEXT NOT NULL,
    login_url TEXT NOT NULL,
    poll_endpoint TEXT NOT NULL,
    poll_token_ref VARCHAR(512) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_pending_login_owner
    ON pending_nextcloud_logins (owner_subject);
CREATE INDEX ix_pending_login_expiry
    ON pending_nextcloud_logins (expires_at);

CREATE TABLE nextcloud_connections (
    connection_id VARCHAR(256) PRIMARY KEY,
    owner_subject VARCHAR(512) NOT NULL,
    base_url TEXT NOT NULL,
    login_name VARCHAR(512) NOT NULL,
    root_path TEXT NOT NULL,
    credential_ref VARCHAR(512) NOT NULL,
    verify_tls BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_nextcloud_connection_owner
    ON nextcloud_connections (owner_subject);

-- Secret references are intentionally not foreign keys. ConnectionService deletes secrets and
-- metadata explicitly so a transient vault/database failure cannot silently cascade-delete user
-- metadata. A separate maintenance job handles old unreferenced encrypted blobs after a grace
-- period, which also covers process crashes between secret insertion and metadata commit.

COMMIT;
