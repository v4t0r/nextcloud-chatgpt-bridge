# Public plugin submission readiness

This document tracks repository-side preparation for **Nextcloud for ChatGPT & Codex**. It follows
the current [OpenAI plugin submission guidance](https://developers.openai.com/plugins/deploy/submission).
Passing this checklist does not itself publish the plugin or authorize public hosting.

## Submission shape

- submission type: MCP-only initially; optional skills may be added later
- MCP URL type: Universal, because one public endpoint resolves tenant context from OAuth
- product name: Nextcloud for ChatGPT & Codex
- authentication: external OAuth/OIDC at the bridge boundary, Nextcloud Login Flow v2 for account connection
- data plane: request-scoped tenant context -> owned connection -> bounded provider
- product website: https://nextcloud-for-chatgpt.v4t0r.chatgpt.site

OpenAI currently requires a public production URL, accurate tool metadata, public website, support,
privacy and terms URLs, domain verification, reviewer access, and positive plus negative test cases.
The canonical form copy, cases, annotation inventory, reviewer runbook, release notes, and final
checklist live in [`submission/`](../submission/). Deployment and publisher actions are release
gates and are never represented as complete by the source release alone.

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
