# nextcloud-chatgpt-bridge

Open-source bridge for a public **Nextcloud for ChatGPT & Codex** app, with an MCP-first core and standards-based Nextcloud providers.

## Goal

Provide a reusable multi-user connector that lets ChatGPT and Codex work with each user's connected Nextcloud account. Native Nextcloud MCP/API capabilities are preferred when available; WebDAV, CalDAV and CardDAV remain standards-based fallback providers.

## Current status

`v0.1.0` is the first installable developer release. The project now has:

- project bootstrap and CI configuration
- validated runtime configuration
- HTTPS-by-default credential transport
- root-folder security boundaries
- bounded WebDAV upload/download provider
- authenticated OCS capability discovery
- native Nextcloud Context Agent MCP availability probe
- MCP Python SDK v2 server
- structured file tools with read/write risk annotations
- text and small-binary transfer limits
- in-memory MCP integration tests
- sanitized live diagnostics with an explicit opt-in write smoke test
- successful live validation against Nextcloud 33.0.7 using the WebDAV/OCS fallback path
- OAuth/OIDC-protected hosted MCP server factory
- Nextcloud Login Flow v2 account connection without collecting the user's Nextcloud password
- request-scoped bridge identity/session context with issuer-scoped pseudonymous tenant IDs
- tenant-scoped connection metadata and credential-store interfaces
- explicit `pending`, `connected` and `disconnected` connection states
- encrypted PostgreSQL credential storage with tenant-bound AES-GCM authentication data
- versioned database migration, startup schema verification and orphan-secret maintenance
- multi-user isolation and hosted-storage tests

The local/self-hosted bridge and public-app backend foundation are implemented, but the hosted service is not production-ready. Infrastructure-enforced outbound network policy, rate limits, audit/privacy controls, deployment wiring and an end-to-end ChatGPT/Codex OAuth test remain public-service release gates.

## v0.1.0 scope

This release provides an installable local MCP bridge and the tested code foundation for a future public ChatGPT/Codex app. It does **not** publish or authorize a production multi-tenant hosted service. See [SECURITY.md](SECURITY.md) and [docs/HOSTED_ACCEPTANCE.md](docs/HOSTED_ACCEPTANCE.md).

## Planned architecture

```text
ChatGPT / Codex
       |
       | OAuth access token
       v
Public MCP / App boundary
       |
       | request-scoped BridgeSessionContext
       v
ConnectionService
       |-- tenant-scoped metadata store
       `-- tenant-scoped encrypted credential store
       |
       | per-request Nextcloud settings
       v
Existing provider core
       |-- Native Nextcloud MCP / Context Agent
       |-- WebDAV provider (files)
       |-- CalDAV provider (calendar, planned)
       |-- CardDAV provider (contacts, planned)
       `-- OCS / Nextcloud APIs
```

## Current MCP tools

Discovery / read-only:

- `get_nextcloud_capabilities`
- `probe_native_nextcloud_mcp`
- `list_files`
- `get_file_info`
- `read_text_file`
- `download_file_base64`

Write / modify:

- `write_text_file`
- `upload_file_base64`
- `create_folder`
- `move_file`
- `delete_file`

Hosted account connection:

- `begin_nextcloud_connection`
- `poll_nextcloud_connection`
- `list_nextcloud_connections`
- `set_nextcloud_root`
- `disconnect_nextcloud`

See [docs/MCP.md](docs/MCP.md) for core tools and [docs/AUTH_ARCHITECTURE.md](docs/AUTH_ARCHITECTURE.md) for public-app identity, connection and credential boundaries.

## Security defaults

- bridge OAuth identity and Nextcloud credentials are separate security domains
- hosted requests derive a fresh immutable session context from the verified access token
- tenant IDs are pseudonymous hashes of the verified issuer and subject
- every connection and credential lookup is tenant-scoped
- Nextcloud app passwords are referenced from metadata, never embedded in it
- production credential storage encrypts at rest with tenant-bound AES-256-GCM
- dedicated Nextcloud service user recommended for stronger Nextcloud-side isolation
- access restricted to a configured root such as `/ChatGPT`
- account-root access refused by default
- parent-path traversal rejected before network access
- out-of-root WebDAV `href` values discarded
- HTTPS required by default; TLS verification enabled by default
- local mode loads credentials from environment variables / local `.env`
- hosted mode uses Nextcloud Login Flow v2 and never asks for the user's Nextcloud password
- secrets must never be committed
- overwrite disabled by default
- configured root can never be deleted
- transfer size limits enforced in both MCP and WebDAV layers
- remote response bodies are not reflected into MCP error messages
- native MCP probing invokes discovery only, never a remote native tool
- native MCP bearer-token requests do not follow redirects
- local Streamable HTTP binds to `127.0.0.1` by default
- hosted deployment still requires infrastructure egress controls, rate limits and operational hardening

See [SECURITY.md](SECURITY.md).

## Development

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
```

Install `.[hosted]` for PostgreSQL-backed connection metadata and encrypted credential storage. Hosted secrets and database URLs are deployment configuration and must never be committed.

Release artifacts contain a wheel, source archive and `SHA256SUMS`. After installing the wheel, `nextcloud-chatgpt-schema` prints the packaged PostgreSQL migration for review/application by an operator.

Copy `.env.example` to `.env` only for local testing and replace placeholders with a dedicated Nextcloud account/app password.

Run the MCP server over stdio:

```bash
nextcloud-chatgpt-bridge
```

or:

```bash
python -m nextcloud_chatgpt_bridge
```

## Live diagnostics

Read-only connectivity/capability check:

```bash
nextcloud-chatgpt-diagnose
```

Explicit write smoke test:

```bash
nextcloud-chatgpt-diagnose --write-test
```

The write test creates one randomized temporary folder below `NEXTCLOUD_ROOT_PATH`, verifies create/upload/download/move, and then removes the folder. Diagnostics emit sanitized JSON and never print credentials or remote response bodies.

The first live validation passed against Nextcloud 33.0.7 with OCS, WebDAV read/write and cleanup all successful. Native Context Agent MCP was not available, confirming the fallback design works in a real deployment. See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Roadmap

1. project bootstrap and CI — implemented
2. WebDAV files MVP — implemented and live-validated
3. MCP tool layer — implemented
4. native Nextcloud capability/MCP detection — implemented; fallback live-validated
5. public multi-user connection/auth/storage foundation — implemented; deployment integration pending
6. `v0.1.0` installable developer release — implemented
7. infrastructure egress enforcement, rate limiting and audit/privacy controls
8. end-to-end ChatGPT/Codex OAuth and account-connection validation
9. search, shares, tags and versions
10. CalDAV and CardDAV support
11. security review, app submission and public hosted-service release

## License

Licensed under the [Apache License 2.0](LICENSE). See [CHANGELOG.md](CHANGELOG.md) for release history.
