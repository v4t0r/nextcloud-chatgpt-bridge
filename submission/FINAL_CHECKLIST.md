# Final OpenAI submission checklist

This is the last-mile handoff. Checked items are repository-side deliverables. Unchecked items require
real production or publisher state and must not be marked complete with placeholders.

## Repository package

- [x] Product name, short description, long description, category, and starter prompts
- [x] Public hosted tool set locked by automated contract tests
- [x] Explicit titles, descriptions, input/output schemas, and risk annotations
- [x] Positive and negative reviewer cases
- [x] Disposable reviewer fixture specification and runbook
- [x] OAuth-protected universal MCP application
- [x] Tenant isolation and encrypted credential storage
- [x] DNS-rebinding-resistant egress reference and isolated network composition
- [x] Rate limits, request limits, security headers, health, migration, and maintenance controls
- [x] Domain-challenge route disabled unless an exact portal token is configured
- [x] Product, support, security, privacy, and terms website source
- [x] Codex plugin manifest, skill, artwork, and marketplace entry
- [x] Release notes, deployment guide, privacy model, terms boundary, and security policy

## Verified OpenAI portal state (2026-08-28)

- [x] Organization account is verified
- [x] Submitter is an organization owner with Apps Management read/write access
- [x] Global-residency project `NC-GPT-APP` is selected
- [x] Standard **With MCP** draft can be created and is saved in the portal
- [x] Square PNG artwork is available for both the 256 px directory and 48 px composer slots
- [x] A verified individual identity is selectable in the Developer Identity field
- [x] Selected individual publisher identity and controller name match the public listing and legal pages (2026-09-25)

## Production environment

- [x] Public MCP domain resolves to the reviewed deployment (2026-09-09)
- [x] TLS and trusted proxy/host configuration validated (2026-09-09)
- [x] Identified NPM 2.15.1 command-injection path patched with upstream `a5db5ed`, regression-tested and verified on the running proxy image (2026-09-25)
- [ ] External OAuth discovery, JWKS, audience, scopes, PKCE, and client mode validated
- [ ] PostgreSQL backup/restore and credential-key rotation tested
- [x] Daily encrypted bridge/Keycloak backups, 30-day local retention, and archive integrity checks configured (2026-09-25); off-host copy and restore drill remain open
- [ ] Monitoring, alerting, incident response, log retention, and abuse response approved
- [x] Seven-day host journal retention applied to all seven production containers (2026-09-25)
- [x] Hosting, controller, and self-hosted OAuth arrangements published in the privacy notice (2026-09-25)
- [ ] Concrete metadata, log, backup, inactive-account, and financial-data retention published
- [ ] User export, disconnect, revocation, and deletion procedures tested
- [x] Public website, support, privacy, and terms URLs return HTTPS 200 (2026-09-09)
- [x] `nextcloud-chatgpt-preflight` passes against exact production URLs (2026-09-09; domain challenge not yet configured)
- [ ] Full hosted acceptance runbook passes with two isolated tenants

## Reviewer fixture

- [ ] Disposable bridge reviewer identity created without MFA or private-network dependency
- [ ] Disposable non-admin Nextcloud account contains only synthetic fixture data
- [ ] Reviewer connection root is restricted to the synthetic workspace
- [ ] Positive and negative cases pass from ChatGPT
- [ ] Positive and negative cases pass from Codex where the review surface is available
- [ ] Reviewer credentials stored only in OpenAI's protected submission field

## Publisher portal

- [x] OpenAI individual publisher identity verified and visible in the selected project
- [x] Publishing route chosen: verified individual identity
- [x] Publisher name and legal/public pages aligned with the chosen verified identity (2026-09-25)
- [x] Standard **With MCP** draft created in the global-residency project
- [x] Version, name, subtitle, descriptions, category, and both icon slots saved in the draft
- [x] Exact production MCP URL entered
- [x] Exact website, support, privacy, and terms URLs entered; corrected public legal content deployed as Site version 5 (2026-09-25)
- [x] Listing copy saved in the draft
- [ ] Demo recording URL entered
- [ ] Commerce and purchasing declaration completed
- [ ] Reviewer instructions and credentials entered
- [x] Domain challenge token configured privately on the production VM (2026-09-25)
- [x] Domain challenge passes byte-for-byte and is verified in the portal (2026-09-25)
- [ ] Five positive and three negative cases entered and rerun successfully
- [ ] Country availability, release notes, and policy attestations completed
- [ ] Final metadata preview matches the repository contract
- [ ] Owner deliberately presses **Submit for review**

The 2026-09-25 portal scan now uses pre-defined client ID `nextcloud-chatgpt` and the client secret
entered by the operator. Domain verification passed. The authenticated tool scan is still blocked:
OpenAI requests `openid email offline_access nextcloud:use`, but the deployed Keycloak client rejects
`offline_access` as `invalid_scope`. A read-only authorization probe passes without that scope and
fails with it. The optional client-scope change is prepared, pending explicit authorization because
it can permit offline refresh tokens. The realm currently has no users, so a reviewer identity and
end-to-end scan remain separate gates even after this scope issue is fixed.

## Never include

- real Nextcloud, OAuth, reviewer, database, or encryption credentials in Git
- private Nextcloud URLs, personal files, production tokens, or raw invoice data in evidence
- claims of OpenAI approval or public availability before those states are real
