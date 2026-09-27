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
- [ ] Authenticated OAuth audience and end-to-end client flow validated; public discovery, JWKS, scopes, and PKCE checks pass (2026-09-27)
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

- [x] Disposable bridge reviewer identity `openai-reviewer` created without MFA or private-network dependency (2026-09-27); Nextcloud binding remains open
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

Domain verification passed on 2026-09-25. The `offline_access` scope was linked as an optional
client scope with the operator's approval; the source and deployment were pushed as `fa7e88e`.
On 2026-09-27, all 15 public bridge checks passed and the deployed client retained the exact
callback, PKCE S256, default `email`/`nextcloud:use` scopes, and optional `offline_access`.
The first portal retry attempted dynamic registration despite displaying `Pre-defined`, and
Keycloak correctly rejected it with HTTP 403 `Trusted Hosts`. After the operator re-entered the
pre-defined client secret, a second `Scan Tools` attempt reached the real Keycloak login page
with the expected client ID, redirect, resource, PKCE S256, and requested scopes. A separate
`openai-reviewer` account was then created after explicit approval. Its random password is stored
only on the VM in a mode-0600 file, and its email is not marked verified. **Tool discovery has not
succeeded yet**: the first login attempt used an expired authorization request (`expired_code`).
A fresh portal request reached Keycloak, but the code-to-token exchange failed with `invalid_code`;
the reviewer account had no active Keycloak session afterward. The portal returned to the plugin
list instead of importing tools. A subsequent scan again attempted DCR and received HTTP 403,
while the advanced form still displayed `Pre-defined` and an empty saved-secret placeholder.
After the next browser callback returned to the draft, a repeated `Scan Tools` still reported
`Authentication required`; no imported tools appeared. The browser automation masks the password
field as `<redacted>`, so its displayed value cannot establish whether the secret was persisted.
After the operator entered the secret again, the scan reached `Authorize MCP`, but the callback
returned to the plugin list without imported tools. Keycloak logged another `invalid_code` during
the token exchange at 2026-09-27 19:43:43 UTC. A controlled authorization-code/PKCE test run
directly on the VM with the same reviewer identity, client, callback, resource, and secret-post
method succeeded: token HTTP 200 with the MCP audience and expected scopes. This establishes that
Keycloak can complete the flow, but does not establish why the portal exchange failed. The Codex
desktop restarted at approximately 19:43:23 UTC during this attempt; Windows Application logs
showed no registered application crash or dump. Do not claim portal OAuth or tool-scan success
until the portal lists imported tools. A synthetic Nextcloud connection and authenticated
acceptance evidence also remain required.

## Never include

- real Nextcloud, OAuth, reviewer, database, or encryption credentials in Git
- private Nextcloud URLs, personal files, production tokens, or raw invoice data in evidence
- claims of OpenAI approval or public availability before those states are real
