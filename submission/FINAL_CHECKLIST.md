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
- [ ] Selected publisher identity exactly matches the public listing, website, support, privacy, and terms

## Production environment

- [ ] Public MCP domain resolves to the reviewed deployment
- [ ] TLS and trusted proxy/host configuration validated
- [ ] External OAuth discovery, JWKS, audience, scopes, PKCE, and client mode validated
- [ ] PostgreSQL backup/restore and credential-key rotation tested
- [ ] Monitoring, alerting, incident response, log retention, and abuse response approved
- [ ] Actual hosting and OAuth providers added to privacy disclosures
- [ ] Concrete metadata, log, backup, inactive-account, and financial-data retention published
- [ ] User export, disconnect, revocation, and deletion procedures tested
- [ ] Public website, support, privacy, and terms URLs return HTTPS 200
- [ ] `nextcloud-chatgpt-preflight` passes against exact production URLs
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
- [ ] Publishing route chosen: verified individual identity or separately verified business identity
- [ ] Publisher name and legal/public pages aligned with the chosen verified identity
- [x] Standard **With MCP** draft created in the global-residency project
- [ ] Version, name, subtitle, descriptions, category, and both icon slots completed
- [ ] Exact production MCP URL entered
- [ ] Exact website, support, privacy, and terms URLs entered
- [ ] Listing copy pasted from `submission/LISTING.md`
- [ ] Demo recording URL entered
- [ ] Commerce and purchasing declaration completed
- [ ] Reviewer instructions and credentials entered
- [ ] Domain challenge token copied into the deployment secret
- [ ] Domain challenge passes byte-for-byte and is verified in the portal
- [ ] Five positive and three negative cases entered and rerun successfully
- [ ] Country availability, release notes, and policy attestations completed
- [ ] Final metadata preview matches the repository contract
- [ ] Owner deliberately presses **Submit for review**

## Never include

- real Nextcloud, OAuth, reviewer, database, or encryption credentials in Git
- private Nextcloud URLs, personal files, production tokens, or raw invoice data in evidence
- claims of OpenAI approval or public availability before those states are real
