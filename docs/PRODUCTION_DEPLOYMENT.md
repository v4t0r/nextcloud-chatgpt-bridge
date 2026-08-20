# Production deployment

This guide deploys the reference public MCP boundary. It is a secure baseline, not a substitute for
an operator's privacy, retention, monitoring, backup, and incident-response program.

## Required external services

- a public DNS name dedicated to the MCP service
- an internet-reachable Linux host with current Docker and Docker Compose
- an external OAuth/OIDC authorization server with public HTTPS discovery and JWKS
- a PostgreSQL backup destination outside the application host
- public website, support, privacy, and terms URLs
- a secret manager or root-readable secret files outside Git

Do not use sample domains, preview URLs, local tunnels, or private network addresses for review.

## OAuth contract

Configure and verify:

- exact issuer URL
- exact JWKS URL
- exact MCP audience/resource URL
- required scopes, normally `nextcloud:use`
- pinned JWT algorithms, normally `RS256`
- PKCE `S256`
- one supported ChatGPT client mode: CIMD, dynamic client registration, or a predefined client
- UserInfo plus `openid email` only when the chosen publisher/account flow actually requires it

Issuer, resource, audience, and discovery values are security identifiers. Preserve their exact
configured form rather than relying on slash or redirect normalization.

## Secret files

Create `deploy/secrets/` only on the deployment host. It is ignored by Git.

`database-password.txt` contains one strong PostgreSQL password. `credential-keyring.json` maps a
short key ID to a base64-encoded 32-byte AES key:

```json
{
  "primary": "base64-encoded-32-byte-key"
}
```

Keep historical keys while ciphertext still references them. Change
`BRIDGE_SECRET_ACTIVE_KEY_ID` only after the new key is present on every process. Document and test
the complete rotation and recovery procedure before public launch.

## Configure

Copy `deploy/.env.production.example` to an untracked `deploy/.env.production` and replace every
example value. The MCP resource URL is always `https://<PUBLIC_DOMAIN>/mcp` in the reference
composition.

The bridge process receives only the private PostgreSQL URL assembled from its mounted password,
the credential keyring, exact OAuth configuration, public product URLs, trusted host, and proxy
settings. It never needs a global Nextcloud credential.

## Validate and start

```bash
docker compose --env-file deploy/.env.production \
  -f deploy/compose.production.yml config

docker compose --env-file deploy/.env.production \
  -f deploy/compose.production.yml build --pull

docker compose --env-file deploy/.env.production \
  -f deploy/compose.production.yml up -d
```

The one-shot migration service applies only pending packaged migrations. The bridge refuses
readiness when PostgreSQL is unreachable or the schema version is unexpected. The maintenance
service removes expired login flows and sufficiently old unreferenced encrypted secrets.

## Network invariants

- `bridge`, `database`, `migrate`, and `maintenance` stay on the internal network
- only `egress` and `caddy` join the external edge network
- the bridge keeps `HTTPS_PROXY=http://egress:8080`
- the egress proxy permits CONNECT to port 443 only
- every destination must resolve entirely to global addresses
- the egress proxy connects to a validated IP and does not perform a second DNS lookup
- Caddy is the only public listener and terminates TLS before proxying to the bridge

Do not add direct external connectivity to the bridge container. Doing so invalidates the hosted
SSRF and DNS-rebinding boundary.

## Release preflight

Run from a trusted operator environment with the exact public values:

```bash
BRIDGE_RESOURCE_SERVER_URL=https://mcp.example.com/mcp \
BRIDGE_AUTH_ISSUER_URL=https://auth.example.com/ \
BRIDGE_AUTH_DISCOVERY_URL=https://auth.example.com/.well-known/openid-configuration \
BRIDGE_AUTH_REQUIRED_SCOPES=nextcloud:use \
BRIDGE_AUTH_CLIENT_MODE=cimd \
BRIDGE_WEBSITE_URL=https://www.example.com/ \
BRIDGE_SUPPORT_URL=https://www.example.com/support \
BRIDGE_PRIVACY_URL=https://www.example.com/privacy \
BRIDGE_TERMS_URL=https://www.example.com/terms \
nextcloud-chatgpt-preflight
```

Configure `OPENAI_APPS_CHALLENGE_TOKEN` only after the OpenAI portal issues the exact token. The
preflight then also validates `/.well-known/openai-apps-challenge` byte-for-byte.

## Operations before reviewer access

- back up and restore PostgreSQL in a disposable environment
- exercise credential-key rotation and rollback
- verify disconnect removes local state when Nextcloud revocation succeeds and fails
- define profile, review-report, log, backup, and inactive-account retention
- document user export and deletion handling
- alert on readiness failure, repeated OAuth failure, rate limiting, and egress rejection without
  logging tokens, URLs containing secrets, file contents, or credentials
- run every step in `docs/HOSTED_ACCEPTANCE.md`
- run every reviewer case in `submission/TEST_CASES.md`

## Upgrade and rollback

Build immutable images from a tagged commit. Run the migration service before the new bridge becomes
healthy. Hosted startup never migrates implicitly. Roll back application code only when its expected
schema is compatible; never delete migration history or replace release artifacts for an existing
tag.
