# nextcloud-chatgpt-bridge

Open-source, MCP-first bridge connecting ChatGPT with Nextcloud.

## Goal

Provide a reusable connector that lets ChatGPT work with Nextcloud files first, then calendars, contacts, shares and selected Nextcloud apps. Native Nextcloud MCP/API capabilities are preferred when available; WebDAV, CalDAV and CardDAV remain standards-based fallback providers.

## Current status

Early development. The repository is private while the architecture, authentication model and security boundaries are being validated.

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

## Security defaults

- dedicated Nextcloud service user recommended
- access restricted to a configured root such as `/ChatGPT`
- account-root access refused by default
- parent-path traversal rejected
- TLS verification enabled by default
- credentials loaded from environment variables / local `.env`
- secrets must never be committed
- destructive operations will remain separate capabilities

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

## Roadmap

1. project bootstrap and CI
2. WebDAV files MVP
3. MCP tool layer
4. native Nextcloud capability detection
5. search, shares, tags and versions
6. CalDAV calendar support
7. CardDAV contacts support
8. additional Nextcloud apps
9. security review and public release

## License

No public license has been selected yet. Apache-2.0 is the current candidate for the first public release.
