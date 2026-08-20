BEGIN;

ALTER TABLE nextcloud_connections
    ADD CONSTRAINT uq_nextcloud_connection_tenant_connection
    UNIQUE (tenant_id, connection_id);

CREATE TABLE household_profiles (
    profile_id VARCHAR(256) PRIMARY KEY,
    tenant_id VARCHAR(256) NOT NULL,
    connection_id VARCHAR(256) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    invoice_inbox_path TEXT NOT NULL,
    invoice_archive_path TEXT NOT NULL,
    review_report_path TEXT NOT NULL,
    default_currency VARCHAR(3) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_household_currency_upper CHECK (default_currency ~ '^[A-Z]{3}$'),
    CONSTRAINT fk_household_profile_owned_connection
        FOREIGN KEY (tenant_id, connection_id)
        REFERENCES nextcloud_connections (tenant_id, connection_id)
        ON DELETE CASCADE
);

CREATE INDEX ix_household_profile_tenant
    ON household_profiles (tenant_id);

CREATE UNIQUE INDEX uq_household_profile_connection
    ON household_profiles (tenant_id, connection_id);

-- Household configuration contains paths and currency only. Invoice contents, extracted text,
-- payment data and credentials remain outside the bridge database.

INSERT INTO bridge_schema_migrations (version) VALUES (2);

COMMIT;
