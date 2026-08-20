# Security Policy

## Current status

This project is under active development and not yet intended for production use.

## Security principles

- Least privilege by default.
- Never commit passwords, app passwords, cookies, OAuth tokens, session tokens, API keys or private keys.
- Prefer a dedicated Nextcloud service user with access restricted to a dedicated root such as `/ChatGPT`.
- Refuse account-root access by default.
- Reject path traversal outside the configured root.
- TLS certificate verification is enabled by default.
- Read and write capabilities will be exposed as separate MCP tools so clients can apply distinct approval policies.
- Destructive operations such as delete, overwrite and share creation require explicit capability boundaries.
- Native Nextcloud MCP/API capabilities may be used when available; WebDAV/CalDAV/CardDAV remain isolated provider layers.

## Credential handling

Local development uses environment variables or a `.env` file that must never be committed. `.env.example` contains placeholders only.

For a future public deployment, credentials must be stored by the deployment platform or secret manager, not inside prompts or repository files.

## Reporting vulnerabilities

Until the repository is public, report findings directly to the repository owner. A public disclosure process will be added before the first public release.
