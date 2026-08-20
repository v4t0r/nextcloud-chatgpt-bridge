# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-20

### Added

- Tenant-scoped household profiles bound to an owned Nextcloud connection.
- Idempotent household inbox, archive and review-folder preparation below the configured root.
- Conservative PDF, UTF-8 text and XML invoice extraction with bounded local processing.
- Structured invoice checks, SHA-256 duplicate detection and immutable redacted JSON reports.
- User-visible Nextcloud app and unified-search-provider inventory without administrator APIs.
- Root-bound recursive filename search with deterministic depth, result and scan limits.
- Root-bound read-only share inventory without public URLs or share tokens.
- PostgreSQL schema migration v2 for non-secret household profile metadata.
- Submission-readiness checklist and reviewer-ready positive/negative plugin test cases.

### Security

- Household profiles and every associated operation are tenant- and connection-scoped.
- Invoice review never approves, books, pays, transmits or automatically moves an invoice.
- Full IBANs, raw extracted text, credentials, share tokens and public share URLs are excluded from
  bridge responses and stored review reports.
- Image-only and scanned PDF invoices fail safely into explicit manual/OCR review.
- Global Nextcloud Unified Search is not exposed because it cannot guarantee the configured
  workspace-root boundary; the MCP search tool walks WebDAV only below that root.

## [0.1.0] - 2026-08-20

### Added

- MCP-first Nextcloud file bridge with bounded WebDAV read and write operations.
- Authenticated OCS capability discovery and app-password revocation.
- Read-only native Nextcloud Context Agent MCP discovery.
- OAuth/OIDC-protected hosted MCP server foundation.
- Nextcloud Login Flow v2 account connection model.
- Request-scoped bridge identities and issuer-scoped pseudonymous tenant IDs.
- Tenant-scoped connection and credential-store interfaces.
- AES-256-GCM encrypted PostgreSQL credential storage and schema verification.
- Hosted SSRF preflight policy, orphan-secret maintenance and multi-user isolation tests.
- Sanitized live diagnostics with explicit write and cleanup validation.
- Packaged PostgreSQL migration and reproducible GitHub release workflow.

### Security

- Credentials are separated from bridge identity and connection metadata.
- HTTPS, TLS verification, root-folder boundaries and transfer limits are enabled by default.
- Remote response bodies and credentials are excluded from user-facing errors and diagnostics.
- Public hosted deployment remains blocked until infrastructure egress controls, rate limits,
  privacy controls and production operations are supplied by the deployer.

[0.2.0]: https://github.com/v4t0r/nextcloud-chatgpt-bridge/releases/tag/v0.2.0
[0.1.0]: https://github.com/v4t0r/nextcloud-chatgpt-bridge/releases/tag/v0.1.0
