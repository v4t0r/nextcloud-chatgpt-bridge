# Public plugin submission readiness

This document tracks repository-side preparation for **Nextcloud for ChatGPT & Codex**. It follows
the current [OpenAI plugin submission guidance](https://developers.openai.com/plugins/deploy/submission).
Passing this checklist does not itself publish the plugin or authorize public hosting.

## Submission shape

- portal type: Standard **With MCP**; optional skills may be added later
- MCP URL type: Universal, because one public endpoint resolves tenant context from OAuth
- product name: Nextcloud for ChatGPT & Codex
- authentication: external OAuth/OIDC at the bridge boundary, Nextcloud Login Flow v2 for account connection
- data plane: request-scoped tenant context -> owned connection -> bounded provider
- product website: https://nextcloud-for-chatgpt.v4t0r.chatgpt.site

## Verified portal state

### 2026-09-24 continuation

The existing v1.0.0 draft now contains the product listing, verified individual publisher,
production MCP URL `https://mcp.ooh.world/mcp`, predefined OAuth client ID, three starter prompts,
five positive cases, three negative cases, and release notes. These are saved draft inputs, not
evidence that the reviewer cases have passed or that the plugin has been submitted.

The production OAuth client is enabled with the exact portal callback
`https://chatgpt.com/connector_platform_oauth_redirect`, confidential client authentication and
PKCE S256. The missing `email` client scope was created and attached. Discovery now advertises
`openid`, `email`, `offline_access`, and `nextcloud:use`. The email verification mapper reads the
actual account verification state; it does not manufacture a verified email claim.

Public readiness, authentication challenge, discovery, JWKS and blocked management paths passed
15 live checks. The realm still has no user accounts. Reviewer credentials, a connected synthetic
Nextcloud fixture, full OAuth/two-tenant acceptance, client secret entry, domain verification,
Scan Tools, and a demo recording remain open. Publisher/legal-page alignment and the actual
NPM image's security fix also remain release gates.

### Historical baseline

As of 2026-08-28, the organization is verified, the submitter has Apps Management read/write access,
the global-residency project `NC-GPT-APP` is selected, and the portal accepts a new Standard **With
MCP** draft. This proves submission access, not release readiness. The draft remains unsubmitted.

The portal currently offers a verified individual developer identity, while the public listing and
site identify the maintainer as `v4t0r`. OpenAI requires the verified publisher identity to match the
name, website, support contact, privacy policy, and terms. Choose the individual or business route
and align those materials before entering the final publisher fields.

OpenAI currently requires a public production URL, accurate tool metadata, public website, support,
privacy and terms URLs, domain verification, reviewer access, and positive plus negative test cases.
The canonical form copy, cases, annotation inventory, reviewer runbook, release notes, and final
checklist live in [`submission/`](../submission/). Deployment and publisher actions are release
gates and are never represented as complete by the source release alone.

The observed portal also requires separate directory and composer icons, a semantic version,
subtitle, developer identity, demo recording URL, commerce/purchasing declaration, country
availability, release notes, and policy attestations. The prepared square PNG meets both portal
minimum sizes; the remaining portal values are tracked in `submission/FINAL_CHECKLIST.md`.

## Exact MCP hosting inputs

The repository contains the application and production composition. To create the reviewable
deployment, the operator must provide:

- one controlled public DNS host, normally `mcp.<owned-domain>`, yielding the universal endpoint
  `https://mcp.<owned-domain>/mcp`
- DNS and HTTPS-origin control for `/.well-known/openai-apps-challenge`
- an internet-reachable Linux host or container platform with persistent storage, inbound 80/443,
  outbound HTTPS, and current Docker plus Docker Compose for the reference deployment
- SSH or equivalent deployment access and a non-Git secret manager
- an external OAuth/OIDC issuer with public discovery and JWKS, PKCE S256, audience equal to the
  exact MCP URL, scope `nextcloud:use`, and one supported client mode: CIMD, DCR, or predefined
- UserInfo with verified email plus `openid email` when workspace-domain restrictions are enabled
- a strong PostgreSQL password and AES-256-GCM credential keyring stored outside Git
- named hosting and OAuth providers, regions, subprocessors, and concrete retention/deletion terms
  for the public privacy disclosures
- a no-MFA reviewer bridge identity and a disposable non-admin Nextcloud account containing only
  the synthetic fixture from the reviewer runbook

The bridge does not require an OpenAI model API key and does not call the OpenAI model API. OpenAI
directory publication is also not a runtime dependency: compatible clients can use the hosted MCP
endpoint directly before review, while ChatGPT developer mode can be used for pre-submission tests.

## Tool metadata gate

Before every submission scan:

- every tool has a clear name, description, input schema and structured output
- read-only tools set `readOnlyHint=true`
- tools that create or change private Nextcloud state set `readOnlyHint=false`
- write tools keep `openWorldHint=false` because they operate only inside the user's private system
- overwrite, move, delete, disconnect/revoke and similarly irreversible tools set `destructiveHint=true`
- idempotent hints are used only where repeating the operation does not add a new side effect
- tool responses omit credentials, auth tokens, debug payloads and unnecessary internal identifiers
- share responses omit share tokens and public URLs
- invoice responses omit raw extracted text and full IBAN values

## Reviewer fixture

Prepare a dedicated, non-admin demo identity with a preconnected disposable Nextcloud account. The
account must not require MFA, SMS, email confirmation or private-network access during review. Its
configured bridge root should contain only synthetic data:

- `Documents/household-notes.txt`
- `Household/Invoices/Inbox/energy-2026-0042.txt`
- one private user/group share under the root
- no real names, addresses, payment data or credentials

## Canonical reviewer cases

The authoritative, expanded case set is
[`submission/TEST_CASES.md`](../submission/TEST_CASES.md). The compact minimum below remains a
cross-check for the architecture document.

## Positive test cases

| # | User prompt | Expected behavior | Expected result |
|---|---|---|---|
| 1 | “Show the files directly in my Nextcloud workspace.” | Call `list_files` only. | Root-relative entries; no account-root or credential data. |
| 2 | “Find files named household below my workspace.” | Call `search_files` with bounded depth/results. | Root-relative filename matches plus scan/truncation metadata. |
| 3 | “Which items in my workspace are shared?” | Call `list_nextcloud_shares`. | Root-bound share metadata without token or public URL. |
| 4 | “Review the energy invoice, but do not approve or pay it.” | Call household list/review tools. | Structured fields/checks and explicit human-decision boundary. |
| 5 | “Save the invoice review, then save it again.” | Call the immutable save tool twice. | First `saved=true`; second `saved=false` with duplicate/manual warning. |

## Negative test cases

| # | User prompt or scenario | Expected safe behavior | Reason |
|---|---|---|---|
| 1 | “Read `../secrets.txt` outside my configured workspace.” | Reject before any provider request. | Parent traversal violates the root boundary. |
| 2 | “Approve and pay this invoice automatically.” | Explain that payment/approval is unsupported; perform neither. | The bridge is decision support, not a payment/accounting authority. |
| 3 | Review an image-only invoice without an OCR adapter. | Return manual/OCR-required status and do not invent fields. | Local extraction has no trustworthy text source. |

## Remaining public gates

- deploy the reference network boundary without bypassing its egress and rate controls
- production domain, TLS, and universal MCP endpoint
- external OAuth/OIDC plus exact production discovery/resource metadata
- public website, support, privacy, and terms URLs completed with actual providers
- publisher identity and domain challenge verification
- reviewer bridge identity and disposable synthetic Nextcloud fixture
- documented production retention, deletion, backup, restore, monitoring, and incident response
- final preflight and end-to-end test from ChatGPT and Codex
- OpenAI review approval and deliberate publication by the owner
