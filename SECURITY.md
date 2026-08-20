# Security Policy

## Current status

This project is under active development and not yet intended for production use.

## Security principles

- Least privilege by default.
- Never commit passwords, app passwords, cookies, OAuth tokens, session tokens, API keys or private keys.
- Prefer a dedicated Nextcloud service user with access restricted to a dedicated root such as `/ChatGPT`.
- Refuse account-root access by default.
- Reject path traversal outside the configured root before network access.
- Ignore WebDAV metadata entries whose returned `href` escapes the configured root boundary.
- Require HTTPS for Nextcloud credentials by default; plain HTTP needs an explicit development override.
- TLS certificate verification is enabled by default.
- Never reflect untrusted remote response bodies into MCP error messages.
- Treat file contents, WebDAV metadata, OCS metadata and native MCP metadata as untrusted data.
- Read and write capabilities are exposed as separate MCP tools so clients can apply distinct approval policies.
- Overwrite is disabled by default and deletion of the configured workspace root is always refused.
- Native Nextcloud MCP/API capabilities may be used when available; WebDAV/CalDAV/CardDAV remain isolated provider layers.

## Native Context Agent MCP

The bridge may probe Nextcloud Context Agent at its documented MCP endpoint using the user's Nextcloud app password as a Bearer token.

The probe is intentionally read-only:

- it performs MCP discovery and `list_tools` only
- it does not invoke any native Nextcloud tool
- bearer-token requests do not follow redirects
- reported tool names are bounded, sanitized and truncated before exposure to the outer MCP host
- probe failures are returned without response bodies, tokens or low-level exception details

Native tool invocation is a separate future capability and must not be enabled merely because discovery succeeds.

## Credential handling

Local development uses environment variables or a `.env` file that must never be committed. `.env.example` contains placeholders only.

For a future public deployment, credentials must be stored by the deployment platform or secret manager, not inside prompts or repository files.

## Public multi-tenant deployment blocker

The current network model assumes the bridge operator controls the configured Nextcloud URL. A hosted multi-tenant service that accepts arbitrary Nextcloud URLs would create an SSRF boundary and therefore **must not be released** until it has deterministic outbound-network controls.

At minimum, a hosted release needs:

- URL scheme/hostname validation
- DNS resolution and rebinding protection
- private/link-local/metadata-network policy appropriate to the deployment model
- redirect policy that never forwards credentials to a different origin
- outbound egress restrictions where technically available
- per-tenant secret isolation
- authenticated/authorized public MCP transport
- rate limits, auditability and abuse controls

Self-hosted users may legitimately run Nextcloud on private networks, so these hosted-service controls must not be confused with the local deployment policy.

## Public MCP transport

The current Streamable HTTP mode binds to loopback by default and is a development transport. It is not approved for direct internet exposure. Production deployment requires a proper MCP authorization layer, TLS termination, host/origin protection and production process management.

## Reporting vulnerabilities

Until the repository is public, report findings directly to the repository owner. A public disclosure process will be added before the first public release.
