# Security Policy

## Current status

`v0.3.x` is the supported beta line and the first public-app deployment candidate. The repository
implements the application security boundary and a hardened reference composition, but it does not
claim that a public hosted service is active. A deployer must supply and verify production OAuth,
domains, secrets, retention, monitoring, and reviewer operations before exposure.

## Supported versions

| Version | Security updates |
|---|---|
| `0.3.x` | Supported |
| `0.2.x` | Critical fixes only |
| `0.1.x` | Unsupported |

## Core principles

- Never commit passwords, app passwords, OAuth tokens, API keys, cookies, private keys, or live
  service configuration.
- Keep ChatGPT/Codex-to-bridge identity separate from bridge-to-Nextcloud credentials.
- Derive tenant scope only from a verified OAuth/OIDC issuer and subject, never from tool input.
- Build a fresh immutable `BridgeSessionContext` for every authenticated MCP request.
- Apply tenant predicates to every connection, flow, profile, and credential operation.
- Restrict all file operations to a configured non-root Nextcloud workspace.
- Treat filenames, file bodies, WebDAV/OCS data, native MCP metadata, and invoice text as untrusted.
- Expose reads and writes as separate tools with explicit risk annotations.
- Fail closed on path, identity, schema, credential, transport, and provider ambiguity.

## Identity and credential separation

The public bridge validates JWT signature algorithm, issuer, audience, expiry, subject, and required
scopes. Its tenant ID is a pseudonymous SHA-256 digest of the exact issuer and subject pair, so equal
subjects from different issuers cannot collide.

`BridgeIdentity` and `BridgeSessionContext` contain no Nextcloud username, app password, or credential
reference. The first public version resolves exactly one connected account per tenant for file
operations and refuses to guess when zero or multiple active connections exist.

Nextcloud connection uses Login Flow v2. The user authenticates directly with Nextcloud, including
Nextcloud-managed 2FA. The bridge never asks for the user's Nextcloud password. Generated app
passwords are stored separately from connection metadata.

The production credential store:

- encrypts each credential with AES-256-GCM
- binds tenant ID, credential reference, key ID, and format version as authenticated data
- requires both tenant ID and credential reference for every operation
- supports bounded key IDs for rotation
- deletes the local credential on disconnect even if remote revocation fails

Database passwords and encryption keyrings must remain in the deployment secret manager or mounted
secret files. Managed KMS/HSM envelope encryption is recommended for larger production deployments.

## Workspace boundary

Nextcloud app passwords are account-level credentials, so the selected bridge root is a deterministic
application boundary rather than a Nextcloud token scope.

- account root `/` is refused
- parent traversal is refused before network access
- provider URLs are built below the configured root
- WebDAV responses outside the root are discarded
- overwrite is disabled unless explicitly requested
- deletion of the configured root is always refused
- transfer and request body sizes are bounded

A dedicated Nextcloud service user remains the strongest optional Nextcloud-side isolation for
sensitive deployments.

## Public network boundary

A hosted service accepts a user-supplied Nextcloud hostname and therefore creates an SSRF boundary.
The production reference uses two independent controls:

1. `PublicHostedPolicy` rejects non-HTTPS URLs, embedded credentials, queries/fragments, disallowed
   ports, and any hostname resolving to localhost, private, loopback, link-local, reserved, or other
   non-global addresses.
2. The CONNECT-only egress proxy resolves every HTTPS destination itself, rejects any non-global
   result, and connects to the validated IP rather than resolving the hostname again. The bridge
   container has no direct external network path.

The public MCP process also applies:

- exact trusted-host allowlisting with no wildcards
- MCP transport DNS-rebinding protection
- optional exact origin allowlisting
- per-token and per-client-address rate limits with bounded limiter state
- request body limits
- no-store, HSTS, CSP, frame, referrer, permission, and content-type security headers
- stateless Streamable HTTP and one request-scoped identity per call
- readiness checks for PostgreSQL and the exact schema version

Self-hosted local mode intentionally permits private-LAN Nextcloud servers and must not be exposed
through the public reference boundary without equivalent controls.

## Native Context Agent MCP

Native Nextcloud MCP probing is discovery-only:

- performs MCP initialization and tool listing only
- invokes no native tool
- follows no credential-bearing redirects
- bounds, sanitizes, and truncates reported tool names
- excludes remote response bodies and credentials from errors

Discovery success never authorizes native tool invocation.

## Nextcloud app and share inventory

App discovery uses user-visible navigation and search-provider endpoints, not administrator app
management APIs. Apps without an implemented provider are reported as `detected_only`.

Filename search walks WebDAV only below the configured root with fixed depth, scan, and result caps.
Global Unified Search results are not exposed because their root scope cannot be guaranteed. Share
inventory rechecks every path and omits public URLs and share tokens.

## Household and invoice boundary

Household profiles are tenant-scoped non-secret metadata bound to an owned connection. Invoice
review is advisory and deliberately cannot approve, book, pay, transmit, or automatically archive.

- file paths must remain inside the configured invoice inbox
- supported files are bounded by size, page count, and extracted characters
- image-only or unextractable documents return explicit OCR/manual-review status
- raw extracted text is neither returned nor stored in the profile database
- only the last four IBAN characters may be exposed
- immutable reports are named by SHA-256 and cannot overwrite a duplicate

Saved review reports still contain personal or financial metadata and require an operator-defined
retention and deletion policy inside Nextcloud.

## Operations required before public launch

- production OAuth/OIDC issuer, JWKS, audience, scopes, PKCE, and client-registration mode validated
- external secrets, backup, restore, and key-rotation procedures tested
- production domain, TLS, monitoring, alerting, log retention, and incident response configured
- legal pages completed with the actual hosting and OAuth providers and applicable transfer details
- data deletion and account-disconnect procedures verified
- reviewer identity and synthetic Nextcloud fixture isolated from real data
- `nextcloud-chatgpt-preflight` and the hosted acceptance runbook pass on the exact public endpoints

## Reporting vulnerabilities

Use [GitHub private vulnerability reporting](https://github.com/v4t0r/nextcloud-chatgpt-bridge/security/advisories/new).
Do not put credentials, private URLs, file contents, personal data, or exploit details in a public
issue. If private reporting is unavailable, open a public issue containing only a request for a
private contact channel.
