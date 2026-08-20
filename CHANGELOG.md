# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-08-20

### Added

- Production-facing OAuth-protected universal MCP application with public health, product, and
  opt-in OpenAI domain-challenge routes.
- Trusted-host, transport DNS-rebinding, optional origin, request-body, rate-limit, and response
  security controls for the hosted boundary.
- CONNECT-only HTTPS egress proxy that resolves, validates, and IP-pins public destinations.
- Network-isolated Docker Compose reference with PostgreSQL, migration, bridge, maintenance,
  egress, and Caddy services.
- Explicit pending-migration application and recurring hosted-storage cleanup commands.
- Release preflight for health, protected-resource metadata, OAuth discovery, PKCE, client mode,
  public legal URLs, and domain challenge.
- Codex plugin package, personal marketplace entry, original project artwork, listing copy,
  reviewer runbook, positive/negative cases, and exact tool-annotation inventory.
- Public landing-site source with product, support, security, privacy, and terms pages.

### Changed

- Classified the project as a beta public-app release candidate.
- Preserved exact OAuth URLs instead of normalizing deployment-controlled issuer/resource values.
- Updated release, architecture, security, privacy, and deployment documentation for public review.

### Security

- The bridge container has no direct external route in the reference composition; Nextcloud HTTPS
  traffic must cross the destination-validating egress proxy.
- Hosted MCP requests derive a new verified tenant context and apply bounded token/IP rate limits.
- Production tool contracts require explicit read-only, destructive, idempotent, and open-world
  annotations while retaining deterministic server-side enforcement.
- Public release remains gated on real OAuth, domains, operator policies, reviewer fixtures, and
  successful OpenAI review; this source tag does not activate a hosted service.

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

[0.3.0]: https://github.com/v4t0r/nextcloud-chatgpt-bridge/releases/tag/v0.3.0
[0.2.0]: https://github.com/v4t0r/nextcloud-chatgpt-bridge/releases/tag/v0.2.0
[0.1.0]: https://github.com/v4t0r/nextcloud-chatgpt-bridge/releases/tag/v0.1.0
