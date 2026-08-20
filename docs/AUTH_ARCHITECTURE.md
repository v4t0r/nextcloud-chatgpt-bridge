# Authentication and connection architecture

The public plugin has two independent authentication boundaries. They must never be collapsed into one credential.

## 1. ChatGPT / Codex -> Bridge

The published MCP server is an OAuth 2.1 resource server.

- ChatGPT/Codex obtains an access token from a deployment-controlled external OAuth/OIDC authorization server.
- The bridge validates JWT signature, issuer, audience, expiry, subject and required scopes on every HTTP request.
- The MCP server publishes RFC 9728 protected-resource metadata through the MCP Python SDK.
- Public Streamable HTTP stays stateless so request identity is not inherited from an earlier session.
- A fresh `BridgeSessionContext` is created from the verified access token for every MCP request.
- The exact verified OIDC `iss` + `sub` pair is hashed into a stable pseudonymous `tenant_id` used by stores.

Deployment configuration:

- `BRIDGE_AUTH_ISSUER_URL`
- `BRIDGE_AUTH_JWKS_URL`
- `BRIDGE_RESOURCE_SERVER_URL`
- `BRIDGE_AUTH_AUDIENCE`
- `BRIDGE_AUTH_REQUIRED_SCOPES`
- `BRIDGE_AUTH_ALLOWED_ALGORITHMS`

The authorization server is intentionally external. The bridge does not implement password login, token issuance or custom cryptography.

`BridgeIdentity` contains only the verified issuer and subject. `BridgeSessionContext` adds the verified OAuth client ID and scopes. Neither type contains a Nextcloud username, app password or connection secret. The context is request-scoped; no process-global user session is reused between callers.

## 2. Bridge -> user's Nextcloud

Arbitrary self-hosted Nextcloud instances are linked using Nextcloud Login Flow v2 rather than requiring administrators to pre-register an OAuth client on every server.

1. Authenticated bridge user submits a Nextcloud base URL and bridge root, default `/ChatGPT`.
2. Bridge POSTs to `<nextcloud>/index.php/login/v2`.
3. Bridge returns only an opaque flow ID, the Nextcloud login URL and expiry to the UI.
4. Poll token remains server-side and is stored under the caller's tenant ID.
5. User authenticates directly on their own Nextcloud, including Nextcloud-managed 2FA when enabled.
6. Bridge polls the returned endpoint until Nextcloud returns `server`, `loginName` and a generated app password.
7. App password is stored in the credential store; connection metadata stores only a credential reference.
8. File/API operations resolve the connection using the request's `BridgeSessionContext` and tenant ID.
9. Disconnect attempts to revoke the app password using Nextcloud OCS and always deletes the local credential even if remote revocation fails.

The user's actual Nextcloud password is never requested by or returned to the bridge.

## User and tenant isolation

A connection record contains a pseudonymous `tenant_id`, not the raw OIDC subject. The tenant ID is derived from both issuer and subject, so identical subject strings from different identity providers cannot collide. Lookup intentionally returns the same not-found result for missing and foreign connection IDs. This avoids leaking whether another user's connection exists.

Every metadata query includes the tenant predicate. Every credential-store operation requires both `tenant_id` and `credential_ref`. The encrypted store also includes the tenant ID in AES-GCM authenticated data, preventing a database row or ciphertext from being transplanted into another tenant context. Household profile queries likewise require the tenant predicate and bind each profile to an owned connection ID; profile IDs alone never authorize access.

The first public version supports exactly one active Nextcloud connection per tenant for file operations. If zero are connected the operation fails. If more than one exists the operation also fails until explicit connection selection is implemented; the bridge never guesses.

## Connection lifecycle model

Connection-facing responses use explicit states:

- `pending` after Login Flow starts and while user authorization is incomplete
- `connected` after the generated app password is stored and metadata is committed
- `disconnected` after local metadata and credentials are removed

Pending flow IDs and connection IDs are opaque, high-entropy identifiers. A flow is consumed once Nextcloud returns completion credentials, whether local persistence succeeds or fails. On persistence failure the bridge attempts best-effort remote app-password revocation. Disconnect also attempts remote revocation but always removes the local credential to fail closed.

## Root scope

The generated Nextcloud app password is account-level, so `/ChatGPT` is a deterministic bridge-side least-privilege boundary, not a Nextcloud token scope.

- account root `/` is refused
- `..` traversal is refused
- provider URLs are built below the configured root
- WebDAV responses outside the root are discarded
- a dedicated Nextcloud service/user account remains the strongest optional isolation for sensitive deployments

## Public-hosted SSRF boundary

A hosted service accepts a user-supplied Nextcloud hostname. That makes SSRF a release-critical risk.

Application preflight policy rejects:

- non-HTTPS URLs
- embedded URL credentials
- query/fragment-bearing base URLs
- localhost
- private/RFC1918 addresses
- loopback
- link-local, including common cloud metadata ranges
- reserved/non-global IPs
- ports other than explicitly allowed hosted ports
- DNS names if any resolved address is non-global

Application preflight is not sufficient by itself because DNS can change between validation and
socket connection. The production reference therefore routes every external HTTPS connection
through a CONNECT-only egress proxy. The proxy resolves and validates the destination, rejects the
entire target when any resolved address is non-global, and connects to the validated IP without a
second DNS lookup. The bridge container is attached only to an internal network and has no direct
external route. Local/self-hosted mode intentionally permits private-LAN Nextcloud servers.

Hosted composition must use `build_hosted_connection_service`, which constructs `LoginFlowClient`
with `PublicHostedPolicy`. The reference deployment additionally sets the egress proxy through
`HTTPS_PROXY` and permits only PostgreSQL and proxy traffic on the internal network. Direct
`ConnectionService` construction remains available for local development and tests where
private-LAN Nextcloud hosts are legitimate.

## Secret storage

`InMemoryCredentialStore`, `InMemoryConnectionStore` and `InMemoryHouseholdProfileStore` exist only
for tests/development. Hosted storage uses SQLAlchemy/PostgreSQL connection metadata plus
`EncryptedDatabaseCredentialStore` with AES-256-GCM and bounded key rotation. Migrations are
packaged under `nextcloud_chatgpt_bridge/migrations`; `nextcloud-chatgpt-schema --list` shows
available versions, `--apply` applies only pending versions through an explicit operator action,
and hosted startup requires the exact expected schema version. The maintenance process removes
expired flows and old unreferenced encrypted secrets.

The household table stores display name, root-relative inbox/archive/report paths and default
currency. It stores no Nextcloud credentials, invoice bytes, extracted text, review contents or
payment instructions. A composite tenant/connection foreign key enforces ownership and cascades
profile deletion when a connection is removed. Immutable review JSON remains in the caller's
bounded Nextcloud workspace.

Database URLs and encryption keys are deployment secrets. Plaintext app passwords must never be written to logs, prompts, GitHub, analytics or metadata tables. A managed KMS/HSM envelope-encryption boundary remains recommended for public production deployment.

## Production composition

The reference composition includes PostgreSQL, one stateless bridge worker, an isolated egress
proxy, a maintenance process, migration job, and Caddy TLS termination. It adds bounded in-process
rate limiting, exact trusted hosts, optional exact origins, security headers, body limits, liveness,
readiness, and an OpenAI domain-challenge endpoint that remains disabled until a challenge token is
explicitly configured.

See `deploy/compose.production.yml` and `docs/PRODUCTION_DEPLOYMENT.md`.

## Remaining external release gates

- external OAuth/OIDC provider deployment and end-to-end ChatGPT/Codex OAuth acceptance
- operator-approved log, retention, deletion, backup, restore, and key-management procedures
- public MCP domain, legal/support URLs, and OpenAI domain verification
- reviewer-ready bridge identity and disposable synthetic Nextcloud fixture
- verified OpenAI publisher identity and final directory review
