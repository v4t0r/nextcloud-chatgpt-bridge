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

Every metadata query includes the tenant predicate. Every credential-store operation requires both `tenant_id` and `credential_ref`. The encrypted store also includes the tenant ID in AES-GCM authenticated data, preventing a database row or ciphertext from being transplanted into another tenant context.

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

This preflight is **not sufficient by itself** because DNS can change between validation and socket connection. Public production deployment MUST duplicate the policy at the network/egress layer (proxy/firewall/resolver policy) to prevent DNS rebinding. Local/self-hosted mode intentionally permits private-LAN Nextcloud servers.

Hosted composition must use `build_hosted_connection_service`, which constructs `LoginFlowClient` with `PublicHostedPolicy`. Direct `ConnectionService` construction remains available for local development and tests where private-LAN Nextcloud hosts are legitimate.

## Secret storage

`InMemoryCredentialStore` and `InMemoryConnectionStore` exist only for tests/development. Hosted storage uses SQLAlchemy/PostgreSQL connection metadata plus `EncryptedDatabaseCredentialStore` with AES-256-GCM and bounded key rotation. The schema is packaged at `nextcloud_chatgpt_bridge/migrations/0001_hosted_storage.sql`, can be printed with `nextcloud-chatgpt-schema`, is verified before hosted startup, and is accompanied by cleanup for expired flows and old unreferenced encrypted secrets.

Database URLs and encryption keys are deployment secrets. Plaintext app passwords must never be written to logs, prompts, GitHub, analytics or metadata tables. A managed KMS/HSM envelope-encryption boundary remains recommended for public production deployment.

## Remaining release blockers

- infrastructure egress enforcement for SSRF/DNS-rebinding protection
- external OAuth/OIDC provider deployment and end-to-end ChatGPT/Codex OAuth test
- rate limiting and abuse controls
- audit logging that excludes secrets and file contents
- privacy/retention policy implementation
- managed KMS/HSM integration or a documented equivalent deployment key-management policy
- public domain, legal/support URLs and OpenAI domain verification
