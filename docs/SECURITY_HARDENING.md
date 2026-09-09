# Single-VM security hardening

This runbook complements `SINGLE_VM_DEPLOYMENT.md`. It is not a certification or a claim
that a deployment has no vulnerabilities. Keep environment-specific results outside public Git.

## Host access and firewall

Before disabling passwords, install a persistent operator SSH key and test it in a **new**
connection. Retain ESXi console access for recovery. Store private keys outside this repository.
Choose the smallest practical administration subnet and verify the current SSH client belongs
to it. Do not infer the administration range from the public reverse proxy address.

On the dedicated Ubuntu VM, from an interactive SSH session:

```bash
sudo env SSH_CONNECTION="$SSH_CONNECTION" bash deploy/harden-host.sh \
  deploy 192.0.2.0/24 192.0.2.111
```

The script requires Docker's iptables `DOCKER-USER` chain; it refuses a different backend.
It preserves existing firewall rules, adds restrictions for SSH and the two backend ports,
and blocks new container ingress on the uplink except NPM traffic to 8081/8082. Established
return traffic is retained. SSH is key-only for the selected user; root login, agent/TCP
forwarding, X11 and tunnels are disabled. The selected ports are also blocked for new IPv6
host connections; this deployment publishes containers on IPv4 only. This is not a general
replacement for rules governing unrelated services added later.

A systemd timer automatically rolls back these additions after ten minutes. The script also
rolls back if its confirmation wait expires after eight minutes. Before confirming, test:

1. A new key-authenticated SSH connection.
2. Public MCP readiness and OAuth discovery.
3. Backend ports blocked from a machine other than NPM.

Only after those checks, create the confirmation marker printed by the script from the new
SSH session. The original interactive session reports `HOST_HARDENING_VERIFIED` and cancels
the timer. Do not reboot or change Docker networking while the verification is pending.

Recovery from the ESXi console:

```bash
sudo /usr/local/sbin/nextcloud-hardening-rollback
```

The rollback removes only this script's hooks and SSH drop-in; previous rules remain.
Evidence is root-readable under `/var/lib/nextcloud-bridge/hardening`. The script refuses an
existing installation; inspect it before rerunning. The enabled `nextcloud-firewall` service
reapplies the restrictions after Docker at boot and participates in Docker restarts. Verify
the restrictions again after host/network changes; do not assume reboot persistence was tested.

## Containers

The NPM Compose override applies bounded local logs (three 10 MB files per service), memory,
CPU and process limits. Bridge/egress/maintenance remain non-root with read-only root filesystems,
no capabilities, no-new-privileges and bounded temporary storage. Caddy also runs non-root,
read-only, without capabilities; its upstream low-port file capability is removed at build time.
Keycloak has bounded worker threads, request queue and database pool. Its request-body limit
is 1 MB. Long MCP response streams are not subject to an arbitrary short response deadline.

The PostgreSQL entrypoint still needs initial ownership setup and then runs the database as
the postgres user. Do not blindly drop its initialization capabilities or change volume owners.
Neither database nor the Keycloak management port is published to the host.

Python, Caddy runtime and PostgreSQL base images are digest-pinned. Caddy is rebuilt from its
released module with explicitly selected patched Go/dependency versions. Distribution security
updates are installed during the image build. Tags/digests alone do not incorporate later fixes:

```bash
docker compose --env-file "$HOME/nextcloud-runtime/production.env" \
  -f deploy/compose.production.yml -f deploy/compose.npm.yml build --pull --no-cache
```

Review the selected base/module versions before rebuilding. Scan candidate images before public
release, record final image IDs, validate Caddy in a network-isolated container, and back up both
databases before recreating services. `compose run caddy` conflicts with the running Caddy's fixed
IP; use `docker run --network none` for its configuration validation instead.

## Vulnerability assessment

Scan actual images, including OS and language packages. Give the scanner only image archives and
its own cache/output directory, not the Docker socket, host secrets or application data. A scan
finding needs a recorded decision: fix available/applied, affected execution path, provider status,
or unresolved. Do not silently ignore HIGH/CRITICAL findings to produce a green report.

An unused SSH library in a web server and a TLS finding in a non-networked privilege-switching
helper are different from an exposed TLS endpoint. Establish that distinction from binary/source
and upstream advisories; a package name or scanner severity alone is insufficient. Unsupported
or unpatched relevant findings remain release blockers. Retest authentication, tenant boundaries,
request limits, egress controls and public metadata after changes.

The upstream NPM is part of the public security boundary. Its version, administrative exposure,
TLS policy and update state require separate verification. Full OAuth flow, tenant acceptance,
backup restoration and independent external testing are separate gates from container readiness.

## References

- [Docker firewall handling](https://docs.docker.com/engine/network/firewall-iptables/)
- [Caddy source builds](https://caddyserver.com/docs/build)
- [Keycloak production configuration](https://www.keycloak.org/server/configuration-production)
- [Debian security tracker](https://security-tracker.debian.org/tracker/)
