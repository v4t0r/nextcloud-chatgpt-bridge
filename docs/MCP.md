# MCP server

The bridge uses the official Model Context Protocol Python SDK v2.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

Populate `.env` with a dedicated Nextcloud account and an app password. Keep the account restricted to the intended workspace where possible.

## Run over stdio

```bash
nextcloud-chatgpt-bridge
```

Equivalent:

```bash
python -m nextcloud_chatgpt_bridge
```

## Run over Streamable HTTP for local development

```bash
nextcloud-chatgpt-bridge --transport streamable-http --host 127.0.0.1 --port 8000
```

The HTTP transport is intentionally bound to loopback by default. Do **not** expose the development HTTP server directly to the internet. Public deployment requires a proper MCP authorization layer, TLS termination, host validation and production process management.

## Current tools

### Discovery / read-only

- `get_nextcloud_capabilities`
- `probe_native_nextcloud_mcp`
- `list_files`
- `get_file_info`
- `read_text_file`
- `download_file_base64`

`get_nextcloud_capabilities` uses the authenticated OCS capabilities endpoint to inspect server/app hints. `probe_native_nextcloud_mcp` connects to Nextcloud Context Agent's documented MCP endpoint, authenticates with the app password as a Bearer token, and calls only MCP discovery/listing. It never invokes a native Nextcloud tool.

### Write / modify

- `write_text_file`
- `upload_file_base64`
- `create_folder`
- `move_file`
- `delete_file`

MCP tool annotations identify read-only and destructive operations for compatible hosts. These annotations are UX hints only; deterministic safety is enforced in the provider and configuration layers.

## Hybrid provider selection

The intended provider order is:

1. inspect OCS capabilities
2. probe native Context Agent MCP when available
3. prefer native tools where they offer an equivalent capability and their permissions are appropriate
4. fall back to WebDAV for file operations
5. later use CalDAV, CardDAV and OCS APIs for capabilities not provided natively

Native tool discovery is bounded to 200 tool names, each sanitized and truncated before being returned to the outer MCP host.

## File-transfer limits

Text and base64 transfers are limited by `NEXTCLOUD_MAX_TRANSFER_BYTES`.

Default: `4000000` bytes.

Hard configuration maximum: `25000000` bytes.

The base64 tools are intended as a generic interoperability fallback for small files. Large-file and ChatGPT-native file handoff will be implemented separately so binary payloads do not have to pass through model context as huge base64 strings.

## Security boundaries

- all WebDAV paths stay below `NEXTCLOUD_ROOT_PATH`
- account root `/` is rejected
- `..` traversal is rejected before a network request
- WebDAV responses whose `href` escapes the configured root are ignored
- HTTPS is required by default for Nextcloud credentials
- TLS certificate verification is enabled by default
- remote response bodies are never echoed into tool errors
- overwrite defaults to `false`
- deletion of the configured root is always refused
- remote file contents and remote MCP metadata are treated as untrusted data
- native MCP bearer-token requests do not follow redirects
- native MCP probing invokes no remote tool

## Hosted-service warning

The current architecture is safe for a local/self-hosted bridge where the operator controls the configured Nextcloud URL. A future public multi-tenant hosted service needs additional SSRF/egress controls before accepting arbitrary user-supplied Nextcloud URLs. This is a release blocker, not an optional hardening task.

## Testing

```bash
ruff check .
pytest --cov=nextcloud_chatgpt_bridge --cov-report=term-missing
```

The MCP tests use the SDK's in-memory `Client`, so they validate the same advertised tool schemas and structured results a real MCP host receives without opening a socket.
