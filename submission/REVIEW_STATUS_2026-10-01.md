# OpenAI review checkpoint: 2026-10-01

Plugin: **Nextcloud for ChatGPT & Codex**. Package version: `1.0.0`.
Plugin ID: `plugin_asdk_app_6a91e995840081918f48e8cd5d8cefff`.
Production bridge version: `0.3.1`.

## Verified portal state

- Publication: **Not published**.
- Package review: **In review**.
- MCP configuration: **Configured**, OAuth **Authorized**, domain **verified**.
- The scan dated 2026-09-30 18:13:35 (Europe/Berlin) held 19 tools:
  13 findings challenged `openWorldHint: false` because of external-system access;
  six findings stated only that further review was needed.
- A fresh MCP scan completed on 2026-10-01 at 06:17:02 (portal display, Europe/Berlin).
  It read the newly deployed descriptions. Six tools still have the external-system finding:
  `get_file_info`, `upload_file_base64`, `move_file`, `delete_file`,
  `prepare_household_workspace`, and `save_household_invoice_review`.
  The other 13 listed tools now show only "This tool update needs further review before it can go live."
- Package status remains **In review** and publication remains **Not published**.

The external-hosting finding conflicts with the documented allowance for bounded private accounts
in the [OpenAI annotation reference](https://developers.openai.com/plugins/reference#annotations)
and [remote MCP review guidance](https://developers.openai.com/plugins/deploy/app-review).
No annotation value was changed merely to bypass that finding.

## Action completed

Commit `4ae7e25` clarifies the existing account/workspace boundary in tool descriptions and server
instructions. File paths cannot select unrelated hosts or escape the owned connection's root.
These tools do not browse the public web, create public shares, or send to arbitrary recipients.
Only Login Flow tools accept a user-selected Nextcloud server; those already advertise
`openWorldHint: true`. Tool schemas, permission enforcement, and annotation booleans are unchanged.

- Twelve local MCP/hosted contract tests passed.
- Another 53 existing tests passed before support escalation, covering settings, request identity,
  connection ownership, WebDAV path boundaries, household isolation, network policy, OCS and JWT
  issuer/audience validation. Code inspection confirmed tenant-scoped connection/profile lookup
  and relative paths anchored to the stored account/root. This is not an exhaustive security audit.
- Production source matched the previous Git revision after normalizing line endings.
- Source backup and the prior Docker image were retained for rollback.
- Updated bridge container is healthy.
- All 17 production preflight checks passed after deployment.
- Fresh reviewer OAuth succeeded; `tools/list` returned 25 tools with the new description.
- Reviewer `list_files` returned the three synthetic root folders.
- Public demo video returned HTTP 200.

## Publication dependency

OpenAI must approve the package and complete required MCP tool checks. Once approved, publish the
approved version through the portal. Do not cancel the pending package review solely to request a
faster decision. Off-host backup and full two-tenant acceptance remain operational follow-ups.

## Technical support draft

Sent to the official Help Center support chat on 2026-10-01, approximately 06:28 Europe/Berlin,
after the user conditionally authorized escalation and the additional boundary tests passed.
The existing publisher account was used to authenticate; the conversation acknowledged receipt.
The AI-assisted support agent requested an exact annotation block and confirmation of fixed
per-connection hosts. Both were provided from the current scanned definition and inspected code.
The chat confirmed "Escalated to a support specialist" and stated that replies will also be sent
via email in the coming days. No case number or guaranteed response date was displayed.

Subject: Bounded-private-account openWorldHint findings contradict documented guidance

Our plugin `plugin_asdk_app_6a91e995840081918f48e8cd5d8cefff`, Nextcloud for ChatGPT & Codex,
version 1.0.0, is in review. After the 2026-10-01 rescan, six tools marked `openWorldHint: false`
still receive an external-system finding: `get_file_info`, `upload_file_base64`, `move_file`,
`delete_file`, `prepare_household_workspace`, and `save_household_invoice_review`.
Thirteen other tools are held only for further review. The reference and review documentation
explicitly allow false for a bounded private account/workspace even when externally hosted.
Documentation: https://developers.openai.com/plugins/reference#annotations and
https://developers.openai.com/plugins/deploy/app-review.

These tools use the authenticated user's stored Nextcloud connection. Their relative paths cannot
choose arbitrary hosts or escape the configured root. They do not create public shares, browse the
public web, or send content to arbitrary recipients. Login Flow tools accepting a user-selected
host are already marked true. We have clarified these boundaries in the live tool descriptions
and instructions; the completed rescan demonstrably read these descriptions. OAuth, all 25 tool definitions, the synthetic reviewer file
list, and 17 production preflight checks were verified successfully.
An additional 53 tests passed, including tenant ownership, root traversal protection and
issuer/audience validation. These tests do not claim exhaustive absence of bugs.

Please assess the private-account classification and advise whether additional evidence or a
specific metadata change is required. This is a request to resolve a technical classification
conflict, not a request to expedite the review. No credentials are included in this message.
