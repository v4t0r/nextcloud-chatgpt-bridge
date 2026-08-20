# Hosted multi-user acceptance test

This acceptance test is required before operating the bridge as a public multi-tenant service. It
is intentionally separate from the local WebDAV/OCS/household live diagnostics used for source
releases.

## Required environment

- external OAuth/OIDC provider with pinned issuer, audience, JWKS and scopes
- PostgreSQL initialized with the packaged migration
- deployment encryption key supplied outside the repository
- TLS termination and trusted-proxy configuration
- DNS-rebinding-safe egress proxy/firewall policy
- two independent test identities and one dedicated Nextcloud test account per identity

## Acceptance flow

1. Authenticate as bridge user A and start Nextcloud Login Flow v2.
2. Complete the login directly at Nextcloud and confirm the bridge reaches `connected`.
3. Verify user A can list, read, create, move and remove data only below the configured root.
4. Authenticate as user B and verify A's flow ID, connection ID and credential reference all return
   the same not-found behavior as nonexistent identifiers.
5. Connect user B and verify each tenant resolves only its own Nextcloud settings.
6. Restart the bridge and verify both encrypted connections survive without plaintext secrets.
7. Disconnect user A, confirm local metadata and encrypted secret deletion, and verify remote app
   password revocation when Nextcloud is reachable.
8. Repeat disconnect with simulated Nextcloud failure and confirm local deletion still succeeds.
9. Inspect logs and traces to confirm they contain no tokens, app passwords or file contents.
10. Run rate-limit, retention/deletion and egress-policy failure tests before public exposure.
11. Configure one household profile per tenant and verify profile IDs, invoice paths and reports
    return not-found behavior across tenants.
12. Verify an attempted invoice path escape makes no provider request and duplicate reports cannot
    overwrite an existing hash.
13. Run the reviewer-ready positive and negative cases from `docs/PLUGIN_SUBMISSION.md` through both
    ChatGPT and Codex.

Passing the local `nextcloud-chatgpt-diagnose --write-test` command does not substitute for this
hosted acceptance test because direct app-password configuration bypasses OAuth and Login Flow.
