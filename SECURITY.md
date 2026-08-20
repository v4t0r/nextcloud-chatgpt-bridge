# Security Policy

## Current status

`v0.2.x` is a developer/self-hosted release and is not intended to operate as an internet-facing
public multi-tenant service. The hosted multi-user identity, connection, encrypted-storage and
household-workflow foundations are implemented; infrastructure and operational release gates
remain.

## Supported versions

| Version | Security updates |
|---|---|
| `0.2.x` | Supported |
| `0.1.x` | Critical fixes only |
| `< 0.1.0` | Unsupported development snapshots |

## Security principles

- Least privilege by default.
- Never commit passwords, app passwords, cookies, OAuth tokens, session tokens, API keys or private keys.
- Keep the ChatGPT/Codex-to-bridge identity boundary separate from bridge-to-Nextcloud credentials.
- Derive tenant scope only from a verified OAuth/OIDC issuer and subject, never from tool input.
- Resolve a fresh immutable bridge session context for each authenticated MCP request.
- Apply tenant predicates to metadata and credential reads, writes and deletes.
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
- Never expose global search results when the configured workspace root cannot be enforced.
- Never return Nextcloud share tokens or public share URLs from inventory tools.
- Treat invoice files and extracted fields as untrusted data, never as executable instructions.

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

Hosted account connection uses Nextcloud Login Flow v2. The user authenticates directly with Nextcloud; the bridge receives a generated app password and never asks for the user's Nextcloud password.

Connection metadata stores only an opaque `credential_ref`. The credential-store interface requires both the pseudonymous tenant ID and credential reference for every operation. The included PostgreSQL implementation:

- encrypts credentials with AES-256-GCM
- binds tenant ID, credential reference, key ID and format version as authenticated data
- supports key rotation through bounded key IDs
- never returns another tenant's credential, even if its reference is supplied
- deletes local credentials during disconnect even when remote revocation fails

Deployment encryption keys and database credentials remain outside the repository. A managed KMS/HSM envelope-encryption integration is still recommended before public production use.

## Bridge identity and tenant isolation

The hosted MCP token verifier pins signature algorithm, issuer, audience, expiry and required scopes. A request-scoped `BridgeSessionContext` is created from the verified token. Its tenant ID is a stable pseudonymous SHA-256 digest of the exact OIDC issuer and subject pair.

This design prevents same-value `sub` claims from different issuers from sharing data if multi-issuer authentication is introduced later. Connection and pending-flow IDs return the same not-found behavior for missing and foreign tenants. No process-global user identity or Nextcloud credential is cached between requests.

## Household and invoice boundary

Household profiles are non-secret metadata records keyed by both tenant and owned Nextcloud
connection. A caller cannot select a tenant ID in tool input. Profile lookup, workspace setup,
candidate listing, invoice review and report storage all use the request-scoped tenant context.
Hosted persistence enforces the tenant/connection pair with a composite foreign key and removes
profile metadata when its connection is deleted.

Invoice review is deliberately advisory:

- files must stay inside the profile's configured invoice inbox
- transfer limits are checked before download and oversized supported files are not listed
- PDF parsing is limited to 100 pages and extracted text to 200,000 characters
- image-only documents and PDFs without extractable text require explicit future OCR/vision review
- raw extracted text is never returned or persisted in the profile database
- only the last four IBAN characters may appear in a review
- review reports are named by SHA-256 and written without overwrite
- an existing file hash becomes an explicit duplicate/manual-review result
- no tool approves, books, pays, transmits or automatically moves an invoice

Stored JSON reports contain structured invoice metadata needed for human review. Deployers must
treat those reports as personal/financial data and apply Nextcloud access control, retention and
deletion policies accordingly.

## Nextcloud app access

App discovery uses the authenticated user's navigation and search-provider endpoints, not
administrator app-management APIs. Apps without an implemented provider are reported as
`detected_only`; detection never implies authorization to invoke that app.

The exposed filename search walks WebDAV below `NEXTCLOUD_ROOT_PATH` with fixed depth, result and
scan caps. Nextcloud Unified Search providers are inventoried but global provider search is not
exposed because its results cannot be guaranteed to remain inside the bridge root. Share listing
passes a root-bound path to OCS, rechecks every returned path and excludes share tokens and URLs.

## Public multi-tenant network boundary

Hosted mode accepts user-supplied Nextcloud URLs and therefore creates an SSRF boundary. Application preflight validation is implemented, but a public service **must not be released** until deterministic outbound-network controls duplicate that policy after DNS resolution and at connection time.

Implemented application controls include:

- HTTPS-only hosted targets and allowed-port policy
- rejection of embedded credentials, query strings and fragments
- rejection of localhost, private, loopback, link-local, reserved and other non-global addresses
- same-origin Login Flow URLs and completion server validation
- no credential-bearing redirects in the native MCP probe
- per-tenant metadata and encrypted credential isolation
- OAuth/OIDC-protected hosted MCP construction

Remaining public release gates include:

- DNS-rebinding-safe outbound proxy/firewall/resolver enforcement
- rate limits and abuse controls
- secret-free audit logging
- privacy, retention and deletion policy enforcement
- financial-data retention and redacted household audit controls
- production process management and deployment monitoring

Self-hosted users may legitimately run Nextcloud on private networks, so these hosted-service controls must not be confused with the local deployment policy.

## Public MCP transport

The local Streamable HTTP mode binds to loopback and remains a development transport. The hosted server factory adds OAuth/OIDC resource-server validation and stateless request identity, but it is not a complete deployment. Public exposure still requires TLS termination, host/origin protection, trusted proxy configuration, rate limits and production process management.

## Reporting vulnerabilities

Report findings privately to the repository owner. Do not include live credentials, private file contents or exploit data in a public issue. A dedicated private vulnerability-reporting channel will be documented before the hosted service is submitted publicly.
