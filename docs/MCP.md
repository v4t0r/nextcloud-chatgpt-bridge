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

### Read-only

- `list_files`
- `get_file_info`
- `read_text_file`
- `download_file_base64`

### Write / modify

- `write_text_file`
- `upload_file_base64`
- `create_folder`
- `move_file`
- `delete_file`

MCP tool annotations identify read-only and destructive operations for compatible hosts. These annotations are UX hints only; deterministic safety is enforced in the provider and configuration layers.

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
- TLS verification is enabled by default
- WebDAV response bodies are never echoed into tool errors
- overwrite defaults to `false`
- deletion of the configured root is always refused
- remote file contents are treated as untrusted data

## Testing

```bash
ruff check .
pytest --cov=nextcloud_chatgpt_bridge --cov-report=term-missing
```

The MCP tests use the SDK's in-memory `Client`, so they validate the same advertised tool schemas and structured results a real MCP host receives without opening a socket.
