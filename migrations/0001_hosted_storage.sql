BEGIN;

CREATE TABLE bridge_schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE bridge_secrets (
    secret_ref VARCHAR(256) PRIMARY KEY,
    tenant_id VARCHAR(256) NOT NULL,
    key_id VARCHAR(64) NOT NULL,
    nonce BYTEA NOT NULL,
    ciphertext BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_bridge_secret_nonce_12 CHECK (octet_length(nonce) = 12),
    CONSTRAINT ck_bridge_secret_ciphertext_tag CHECK (octet_length(ciphertext) >= 16)
);

CREATE INDEX ix_bridge_secret_tenant
    ON bridge_secrets (tenant_id);

CREATE TABLE pending_nextcloud_logins (
    flow_id VARCHAR(256) PRIMARY KEY,
    tenant_id VARCHAR(256) NOT NULL,
    root_path TEXT NOT NULL,
    requested_base_url TEXT NOT NULL,
    login_url TEXT NOT NULL,
    poll_endpoint TEXT NOT NULL,
    poll_token_ref VARCHAR(512) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_pending_login_tenant
    ON pending_nextcloud_logins (tenant_id);
CREATE INDEX ix_pending_login_expiry
    ON pending_nextcloud_logins (expires_at);

CREATE TABLE nextcloud_connections (
    connection_id VARCHAR(256) PRIMARY KEY,
    tenant_id VARCHAR(256) NOT NULL,
    base_url TEXT NOT NULL,
    login_name VARCHAR(512) NOT NULL,
    root_path TEXT NOT NULL,
    credential_ref VARCHAR(512) NOT NULL,
    verify_tls BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_nextcloud_connection_tenant
    ON nextcloud_connections (tenant_id);

-- Secret references are intentionally not foreign keys. ConnectionService deletes secrets and
-- metadata explicitly so a transient vault/database failure cannot silently cascade-delete user
-- metadata. A separate maintenance job handles old unreferenced encrypted blobs after a grace
-- period, which also covers process crashes between secret insertion and metadata commit.

INSERT INTO bridge_schema_migrations (version) VALUES (1);

COMMIT;
