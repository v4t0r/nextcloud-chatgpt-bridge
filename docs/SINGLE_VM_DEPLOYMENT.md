# Single VM behind an existing reverse proxy

The base composition plus `deploy/compose.npm.yml` deploys the bridge and a separate Keycloak
authorization server behind NPM. The bootstrap script installs OS prerequisites only. Read the
operator handoff for the actual environment's validation state; infrastructure readiness does not
mean that client login or OpenAI review is complete.

## Base VM

For an initial deployment with the bridge, PostgreSQL, and a separate Keycloak process, start with
4 vCPU, 12 GB RAM, and 80 GB SSD. This is an engineering estimate for initial testing and review,
not a measured concurrency guarantee. Use Ubuntu Server 24.04 LTS on amd64, a fixed internal
address, and an SSH user with sudo. Verify the guest OS against the actual ESXi version.

Keycloak is the self-hosted OAuth/OIDC provider in this composition. It is external to the bridge process,
even when both run on the same VM. A separate physical server is not required.

## Bootstrap commands

Copy the reviewed working tree to the VM first; an uncommitted local script is not available in a
fresh clone from GitHub. From that repository directory:

```bash
bash deploy/bootstrap-ubuntu.sh --help
sudo bash deploy/bootstrap-ubuntu.sh --install
```

The script installs official Docker Engine and the Compose plugin, Python, Git, and VMware guest
tools, then runs Docker's smoke test. It aborts if existing container packages or Docker repository
configuration are detected. It deliberately does not remove packages, alter SSH/firewall rules,
add users to the root-equivalent Docker group, or deploy application containers.

This is a repeatable installation procedure, not a bit-for-bit locked operating-system image.
Installed package versions are recorded in `/var/lib/nextcloud-bridge/bootstrap-packages.txt`.
Record the reviewed source commit and resolved container image digests during application setup.
Use the root account only through sudo; run Docker commands with sudo where required.

## Endpoint and network contract

Use two public hostnames on the existing reverse proxy:

| Purpose | Example |
|---|---|
| MCP resource and audience | `https://mcp.example.com/mcp` |
| Login service | `https://auth.example.com` |
| Proposed Keycloak issuer | `https://auth.example.com/realms/nextcloud` |

The product website may remain at its existing URL. These are separate purposes, not three
different servers. Record the operator's real hostnames outside the public repository.

Before exposing containers, obtain the VM address, reverse-proxy product and source IP, and its TLS
termination mode. Adapt the Caddy edge configuration and published ports to that topology. Do not
start the existing reference composition unchanged: its Caddy configuration assumes direct public
80/443 access and certificate handling.

The existing proxy must preserve Host, Authorization and MCP protocol headers, support streaming
without response buffering, and route the necessary metadata and challenge paths as well as `/mcp`.
Set forwarded headers from trusted proxy information; do not trust arbitrary client-supplied values.
Restrict VM ingress to the actual proxy and administration paths, accounting for Docker's published
port rules. Do not expose PostgreSQL, Docker's API, or Keycloak's management interface publicly.

Keep the bridge's existing isolated network and validated HTTPS egress. If the login hostname
resolves to a private address inside the network, the current egress proxy will reject it. Verify
public DNS and reachability through the external proxy, including NAT loopback where needed.
Do not solve that failure by globally permitting private Nextcloud targets.

### Nginx Proxy Manager topology

For the operator's existing NPM, use one Proxy Host for MCP and one for the login service, each
with its own valid public certificate. Both targets can be on the same VM with separate internal
listening ports. The override publishes MCP on 8081 and login on 8082 at the configured VM IPv4
address. The bootstrap script itself does not provision port mappings.

Turn caching off for both hosts and preserve full request paths. Route MCP metadata and challenge
paths as well as `/mcp`; the login host needs discovery, authorization, token, logout, and static
login resources. Public protocol routes must not have an NPM Basic Auth gate or browser challenge.
Restrict administrative paths separately. Streaming timeout/buffering, forwarded-header trust,
and the proxy-to-VM transport remain deployment checks rather than assumed defaults.

## OAuth configuration to complete on the target

The realm import creates `nextcloud` and a disabled predefined client `nextcloud-chatgpt` with an
empty redirect allowlist. It creates no end users and keeps self-registration off. Configure exact
client redirects and complete an authorization-code/PKCE test before enabling public linking.
Do not use the initial bootstrap administrator as the reviewer account. Public admin/master realm
routes are blocked at the Caddy edge; use the container-local admin CLI for initial provisioning.

## First application deployment

The following values are examples; use the actual VM/proxy addresses and controlled hostnames.
Choose non-conflicting Docker subnets before startup. Fixed Caddy addresses are outside the
dynamic allocation ranges so startup order cannot allocate them to other containers.

```bash
python3 deploy/init-npm-runtime.py \
  --runtime-dir "$HOME/nextcloud-runtime" \
  --vm-ip 192.0.2.84 --npm-ip 192.0.2.111 \
  --mcp-domain mcp.example.com --auth-domain auth.example.com \
  --website https://www.example.com \
  --keycloak-image quay.io/keycloak/keycloak:26.7.3

chmod 0644 deploy/Caddyfile.npm
docker compose --env-file "$HOME/nextcloud-runtime/production.env" \
  -f deploy/compose.production.yml -f deploy/compose.npm.yml config --quiet
docker compose --env-file "$HOME/nextcloud-runtime/production.env" \
  -f deploy/compose.production.yml -f deploy/compose.npm.yml build --pull
docker compose --env-file "$HOME/nextcloud-runtime/production.env" \
  -f deploy/compose.production.yml -f deploy/compose.npm.yml up -d --wait --wait-timeout 240
```

Use sudo for Docker if the operator account is not authorized to manage its socket. The initializer
refuses an existing runtime path so rerunning it cannot silently rotate credentials. Secrets are
created outside the repository in a 0700 directory; individual 0444 files are mounted into
non-root containers. Do not copy those files into the shared workspace or public source tree.

The Caddy edge accepts only the configured NPM source IP plus the expected Host header. It trusts
forwarded client information only from that proxy. The bridge container can reach public HTTPS
only through the existing validated egress proxy. Keycloak and its database use separate internal
networks, and neither database has a host-published port.

## OAuth acceptance after infrastructure startup

Deploy a pinned supported Keycloak release in production mode with PostgreSQL, its own database
credentials, and a canonical HTTPS hostname. Use its documented trusted reverse-proxy settings.
Keep bootstrap administration and client secrets outside Git and logs.

For the first ChatGPT integration, a predefined client is the proposed initial mode. Obtain its exact
redirect URI from the OpenAI portal; do not substitute an assumed callback or wildcard. Check Codex
client registration separately on the intended surface. The integration must prove:

- authorization-code flow with PKCE S256;
- discovery and JWKS with the exact realm issuer;
- access-token audience equal to the exact public MCP resource URL;
- `nextcloud:use` scope, valid signature, expiry, subject and client identity;
- correct handling of the resource parameter and authorization-response issuer;
- refresh/reconnection and rejection of tokens for the wrong audience or tenant.

Do not assert compatibility solely because the provider supports OIDC. Verify actual tokens and
the complete client flow against `auth.py` and the production endpoint. Enable only OIDC scopes
that the client can use. Verified-email/UserInfo support needs real email verification if workspace
domain restrictions are enabled; never hard-code a verified claim.

The Nextcloud Login Flow remains a second, separate connection step. It does not replace the
bridge's OAuth provider.

## Reproducible application setup and acceptance

After the VM/proxy details are known, save the topology-specific Compose configuration, provider
configuration without secrets, version pins, deployment commands, and sanitized acceptance results
alongside the project. Keep the real environment and credentials in ignored or external files.
Do not export a live Keycloak realm containing secrets into the public repository.

Then execute the production guide and hosted acceptance runbook: migrations, readiness, public
preflight, two independent tenants, client login and Nextcloud linking, restart persistence,
disconnect/revocation, and the reviewer cases. Local test-environment repair and source checks are
still required before deployment. Infrastructure provisioning does not complete OpenAI review.

## Publisher

The operator's selected publication route is the verified individual identity. Align publisher and
responsible-party fields with the exact identity once provided securely. Keep the product name
separate from the publisher name. No change to a website URL is implied by this choice.

## Sources

- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Ubuntu release cycle](https://ubuntu.com/about/release-cycle)
- [Keycloak containers](https://www.keycloak.org/server/containers)
- [Keycloak reverse proxy](https://www.keycloak.org/server/reverseproxy)
- [OpenAI authentication](https://developers.openai.com/plugins/build/auth)
- [Production deployment](PRODUCTION_DEPLOYMENT.md)
- [Hosted acceptance](HOSTED_ACCEPTANCE.md)
