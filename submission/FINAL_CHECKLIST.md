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
- [x] Authenticated OAuth authorization-code/PKCE flow, MCP audience, and public `initialize`/`tools/list` validated with a fresh reviewer token (2026-09-27)
- [ ] PostgreSQL backup/restore and credential-key rotation tested
- [x] Daily encrypted bridge/Keycloak backups, 30-day local retention, and archive integrity checks configured (2026-09-25); off-host copy and restore drill remain open
- [ ] Monitoring, alerting, incident response, log retention, and abuse response approved
- [x] Seven-day host journal retention applied to all seven production containers (2026-09-25)
- [x] Hosting, controller, and self-hosted OAuth arrangements published in the privacy notice (2026-09-25)
- [ ] Concrete metadata, log, backup, inactive-account, and financial-data retention published
- [ ] User export, disconnect, revocation, and deletion procedures tested
- [x] Public website, support, privacy, and terms URLs return HTTPS 200 (2026-09-09)
- [x] `nextcloud-chatgpt-preflight` passes all 17 checks against exact production URLs, including domain challenge (reverified 2026-10-01)
- [ ] Full hosted acceptance runbook passes with two isolated tenants

## Reviewer fixture

- [x] Disposable bridge reviewer identity `openai-reviewer` created without MFA or private-network dependency (2026-09-27)
- [x] `NC_bridge_demo` has the synthetic files, invoice, and one private read-only share inside the reviewer workspace (2026-09-28)
- [x] Reviewer connection is bound to `NC_bridge_demo` with root `/ChatGPT-Reviewer` (2026-09-27)
- [x] Public MCP file list, bounded search, text read, private share list, invoice review, and immutable duplicate detection passed with reviewer OAuth (2026-09-28)
- [x] ChatGPT developer-mode smoke test: root list, bounded search, root-wide private share, fictional invoice review, duplicate-safe save, and refusal to pay (2026-09-28)
- [ ] Positive and negative cases pass from ChatGPT
- [ ] Positive and negative cases pass from Codex where the review surface is available
- [x] Reviewer credentials stored only in OpenAI's protected submission field (entered by the owner, 2026-09-28)

## Publisher portal

- [x] OpenAI individual publisher identity verified and visible in the selected project
- [x] Publishing route chosen: verified individual identity
- [x] Publisher name and legal/public pages aligned with the chosen verified identity (2026-09-25)
- [x] Standard **With MCP** draft created in the global-residency project
- [x] Version, name, subtitle, descriptions, category, and both icon slots saved in the draft
- [x] Exact production MCP URL entered
- [x] OpenAI portal `Scan Tools` imported all 25 production tools after the `sub` claim fix (2026-09-27)
- [x] Exact website, support, privacy, and terms URLs entered; corrected public legal content deployed as Site version 5 (2026-09-25)
- [x] Listing copy saved in the draft
- [x] [Public demo recording](https://raw.githubusercontent.com/v4t0r/nextcloud-chatgpt-bridge/main/submission/reviewer-demo.mp4) entered in the draft (2026-09-28)
- [ ] Commerce and purchasing declaration completed
- [x] Reviewer instructions and credentials entered (2026-09-28)
- [x] Domain challenge token configured privately on the production VM (2026-09-25)
- [x] Domain challenge passes byte-for-byte and is verified in the portal (2026-09-25)
- [x] Five positive and three negative cases entered in the draft (2026-09-27)
- [x] Country availability and release notes entered in the draft (2026-09-27)
- [x] Six policy attestations confirmed by the publisher and saved in the review version (2026-09-28)
- [ ] Final metadata preview matches the repository contract
- [x] Publisher explicitly authorized **Submit for Review**; portal confirmed submission and version `1.0.0` shows status `Review` (2026-09-28)

At the 2026-09-28 checkpoint, the submitted OpenAI review version contains 25 imported MCP tools and all 75
annotation justifications. The reviewer identity completes OAuth/PKCE, and its Nextcloud Login Flow
completed under the dedicated root. The bridge's isolated network required deferring public DNS
preflight to the validated egress proxy; this is deployed and the real Login Flow succeeded.
Nextcloud's OCS `subfiles` flag omitted the nested private share, so the bridge now fetches the
bounded share inventory and filters it by the connected workspace root before returning metadata.
The first synthetic invoice review save returned `saved=true`; the second returned `saved=false`
with a duplicate warning. The generated report was removed afterward so reviewers can repeat the
first-save case. In ChatGPT developer mode, the reviewer account listed the synthetic root, found
the private read-only share, reviewed the fictional invoice, saved an immutable report once, rejected
an identical duplicate, and rejected automatic payment. The generated report was deleted again and
the Reviews folder verified empty. The protected test-credential field is saved in the review version.
The public demo recording is linked in the submitted OpenAI version. The portal confirmed submission
and lists version `1.0.0` with status `Review`. Remaining scenario coverage and off-host backup are
operational follow-ups; neither is recorded here as completed.

On 2026-10-01 the portal still reports package `1.0.0` **In review** and **Not published**.
The refreshed MCP scan holds six tools on the private-account/open-world classification and
13 others for further review. Metadata clarification `4ae7e25` is deployed and pushed; fresh reviewer
OAuth, all 25 tool definitions, and the synthetic root list passed. See the
[review checkpoint and technical support draft](REVIEW_STATUS_2026-10-01.md). Publication requires
OpenAI approval and the remaining MCP checks; no approval or publication is claimed.

## Never include

- real Nextcloud, OAuth, reviewer, database, or encryption credentials in Git
- private Nextcloud URLs, personal files, production tokens, or raw invoice data in evidence
- claims of OpenAI approval or public availability before those states are real
