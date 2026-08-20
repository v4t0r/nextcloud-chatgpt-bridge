# Authentication and connection architecture

The public plugin has two independent authentication boundaries. They must never be collapsed into one credential.

## 1. ChatGPT / Codex -> Bridge

The published MCP server is an OAuth 2.1 resource server.

- ChatGPT/Codex obtains an access token from a deployment-controlled external OAuth/OIDC authorization server.
- The bridge validates JWT signature, issuer, audience, expiry, subject and required scopes on every HTTP request.
- The MCP server publishes RFC 9728 protected-resource metadata through the MCP Python SDK.
- Public Streamable HTTP stays stateless so request identity is not inherited from an earlier session.
- The verified `sub` claim is the bridge's stable owner key for Nextcloud connection records.

Deployment configuration:

- `BRIDGE_AUTH_ISSUER_URL`
- `BRIDGE_AUTH_JWKS_URL`
- `BRIDGE_RESOURCE_SERVER_URL`
- `BRIDGE_AUTH_AUDIENCE`
- `BRIDGE_AUTH_REQUIRED_SCOPES`
- `BRIDGE_AUTH_ALLOWED_ALGORITHMS`

The authorization server is intentionally external. The bridge does not implement password login, token issuance or custom cryptography.

## 2. Bridge -> user's Nextcloud

Arbitrary self-hosted Nextcloud instances are linked using Nextcloud Login Flow v2 rather than requiring administrators to pre-register an OAuth client on every server.

1. Authenticated bridge user submits a Nextcloud base URL and bridge root, default `/ChatGPT`.
2. Bridge POSTs to `<nextcloud>/index.php/login/v2`.
3. Bridge returns only an opaque flow ID, the Nextcloud login URL and expiry to the UI.
4. Poll token remains server-side and is stored as a secret.
5. User authenticates directly on their own Nextcloud, including Nextcloud-managed 2FA when enabled.
6. Bridge polls the returned endpoint until Nextcloud returns `server`, `loginName` and a generated app password.
7. App password is stored in the secret store; connection metadata stores only a credential reference.
8. File/API operations resolve the connection by the authenticated bridge OAuth `sub`.
9. Disconnect attempts to revoke the app password using Nextcloud OCS and always deletes the local credential even if remote revocation fails.

The user's actual Nextcloud password is never requested by or returned to the bridge.

## User isolation

A connection record contains an `owner_subject`. Lookup intentionally returns the same not-found result for missing and foreign connection IDs. This avoids leaking whether another user's connection exists.

The first public version supports exactly one active Nextcloud connection per OAuth subject for file operations. If zero are connected the operation fails. If more than one exists the operation also fails until explicit connection selection is implemented; the bridge never guesses.

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

## Secret storage

`InMemorySecretStore` and `InMemoryConnectionStore` exist only for tests/development. Public deployment must use persistent multi-process-safe storage and encrypt Nextcloud app passwords at rest with a deployment secret/KMS boundary. Plaintext app passwords must never be written to logs, prompts, GitHub, analytics or metadata tables.

## Remaining release blockers

- production connection metadata store
- production encrypted secret store / KMS integration
- infrastructure egress enforcement for SSRF/DNS-rebinding protection
- external OAuth/OIDC provider deployment and end-to-end ChatGPT/Codex OAuth test
- rate limiting and abuse controls
- audit logging that excludes secrets and file contents
- privacy/retention policy implementation
- public domain, legal/support URLs and OpenAI domain verification
