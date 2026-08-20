# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/v4t0r/nextcloud-chatgpt-bridge/releases/tag/v0.1.0
