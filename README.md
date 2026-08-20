# nextcloud-chatgpt-bridge

Open-source bridge for a public **Nextcloud for ChatGPT & Codex** app, with an MCP-first core and standards-based Nextcloud providers.

## Goal

Provide a reusable multi-user connector that lets ChatGPT and Codex work with each user's connected Nextcloud account. Native Nextcloud MCP/API capabilities are preferred when available; WebDAV, CalDAV and CardDAV remain standards-based fallback providers.

## Current status

`v0.2.0` is the household-workflow developer release. The project now has:

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
- user-visible Nextcloud app and search-provider inventory without administrator APIs
- root-bound recursive filename search and redacted read-only share inventory
- tenant-scoped household profiles tied to owned Nextcloud connections
- deterministic PDF, UTF-8 text and XML invoice extraction with strict processing limits
- structured invoice checks and immutable, redacted SHA-256 review reports
- PostgreSQL schema migration v2 for non-secret household profile metadata

The local/self-hosted bridge and public-plugin backend foundation are implemented, but the hosted
service is not production-ready. Infrastructure-enforced outbound network policy, rate limits,
audit/privacy controls, deployment wiring and an end-to-end ChatGPT/Codex OAuth test remain
public-service release gates.

## v0.2.0 scope

This release adds household-account configuration, conservative invoice review, scoped app
inventory, root-bound file search and read-only share listing. Invoice review never approves,
books, pays, transmits or automatically archives an invoice. Images and scanned PDFs require a
future explicit OCR/vision adapter and remain in manual review.

`v0.2.0` does **not** publish or authorize a production multi-tenant hosted service. See
[SECURITY.md](SECURITY.md), [docs/HOUSEHOLD_ARCHITECTURE.md](docs/HOUSEHOLD_ARCHITECTURE.md) and
[docs/HOSTED_ACCEPTANCE.md](docs/HOSTED_ACCEPTANCE.md).

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
HouseholdService / app-access boundary
       |-- tenant-scoped profile metadata
       |-- bounded invoice reviewer
       `-- redacted immutable review reports
       |
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
- `get_nextcloud_app_accesses`
- `probe_native_nextcloud_mcp`
- `list_files`
- `search_files`
- `list_nextcloud_shares`
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

Hosted household workflow:

- `configure_household_account`
- `list_household_accounts`
- `prepare_household_workspace`
- `list_household_invoices`
- `review_household_invoice`
- `save_household_invoice_review`

See [docs/MCP.md](docs/MCP.md) for tools,
[docs/AUTH_ARCHITECTURE.md](docs/AUTH_ARCHITECTURE.md) for identity and credential boundaries, and
[docs/PLUGIN_SUBMISSION.md](docs/PLUGIN_SUBMISSION.md) for the public ChatGPT/Codex plugin gate.

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
- global Unified Search is inventory-only; exposed file search stays below the configured root
- share responses omit tokens and public share URLs
- household metadata is tenant-scoped and contains no invoice contents or credentials
- invoice extraction is bounded by file size, page count and extracted-character limits
- review responses omit raw extracted text and reveal only the last four IBAN characters
- duplicate invoice content is detected through SHA-256 and cannot overwrite an existing report
- invoice tools cannot approve, book, pay, transmit or automatically archive documents
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

For a fresh hosted database, the command prints migrations 1 and 2 in order. To upgrade an
existing v0.1 database, review and apply only `nextcloud-chatgpt-schema --version 2` before starting
v0.2; hosted startup intentionally refuses any schema version other than 2.

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

Live validation against Nextcloud 33.0.7 covers OCS, WebDAV read/write and cleanup. The v0.2
acceptance adds app inventory, scoped share discovery and an isolated synthetic household invoice
review. Native Context Agent MCP was not available, confirming the fallback design works in a real
deployment. See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Roadmap

1. bootstrap, WebDAV/OCS core and MCP tool layer — implemented and live-validated
2. multi-user connection, identity and encrypted credential storage — implemented
3. `v0.1.0` installable developer release — implemented
4. root-bound search, read-only shares and user-visible app inventory — implemented in `v0.2.0`
5. household profiles and conservative invoice review — implemented in `v0.2.0`
6. optional OCR/vision and electronic-invoice improvements — planned for `v0.2.1`
7. CalDAV/CardDAV and modular Nextcloud app adapters — planned for `v0.3.0`
8. production hosting, OAuth acceptance and operational security gates — planned for `v0.3.x`
9. OpenAI review and universal Plugins Directory publication — final public-release milestone

See [docs/ROADMAP.md](docs/ROADMAP.md) for milestone boundaries and the planned separation between
the provider-neutral bridge core and any optional OpenAI API/vision integration.

## License

Licensed under the [Apache License 2.0](LICENSE). See [CHANGELOG.md](CHANGELOG.md) for release history.
