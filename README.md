# nextcloud-chatgpt-bridge

Open-source, MCP-first bridge connecting ChatGPT with Nextcloud.

## Goal

Provide a reusable connector that lets ChatGPT work with Nextcloud files first, then calendars, contacts, shares and selected Nextcloud apps. Native Nextcloud MCP/API capabilities are preferred when available; WebDAV, CalDAV and CardDAV remain standards-based fallback providers.

## Current status

Private development repository. The project now has:

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

The next milestone is an end-to-end ChatGPT-to-bridge MCP connection. Production-grade public MCP authentication and hosted-service SSRF controls remain explicit release blockers.

## Planned architecture

```text
ChatGPT
   |
   v
MCP / ChatGPT App
   |
   v
Nextcloud Bridge
   |-- Native Nextcloud MCP / Context Agent
   |-- WebDAV provider (files)
   |-- CalDAV provider (calendar)
   |-- CardDAV provider (contacts)
   `-- OCS / Nextcloud APIs (shares and app capabilities)
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

See [docs/MCP.md](docs/MCP.md) for startup, transport and security details.

## Security defaults

- dedicated Nextcloud service user recommended
- access restricted to a configured root such as `/ChatGPT`
- account-root access refused by default
- parent-path traversal rejected before network access
- out-of-root WebDAV `href` values discarded
- HTTPS required by default; TLS verification enabled by default
- credentials loaded from environment variables / local `.env`
- secrets must never be committed
- overwrite disabled by default
- configured root can never be deleted
- transfer size limits enforced in both MCP and WebDAV layers
- remote response bodies are not reflected into MCP error messages
- native MCP probing invokes discovery only, never a remote native tool
- native MCP bearer-token requests do not follow redirects
- Streamable HTTP binds to `127.0.0.1` by default and is not considered public-deployment ready

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
3. MCP tool layer — implemented; end-to-end ChatGPT connection pending
4. native Nextcloud capability/MCP detection — implemented; fallback live-validated
5. production MCP authentication / deployment boundary
6. search, shares, tags and versions
7. CalDAV calendar support
8. CardDAV contacts support
9. additional Nextcloud apps
10. security review and public release

## License

No public license has been selected yet. Apache-2.0 is the current candidate for the first public release.
