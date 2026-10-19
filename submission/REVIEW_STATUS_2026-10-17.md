# Review and deployment checkpoint — 2026-10-17

## Verified status

- Runtime: 0.3.2 deployed to the existing production VM; bridge, egress and maintenance rebuilt.
- All 17 production preflight checks passed after deployment.
- Fresh reviewer authorization-code OAuth succeeded. Authenticated `tools/list` returned 25 tools;
  `list_files` returned the three synthetic reviewer root folders.
- A fresh encrypted database/recovery backup and previous source/images were retained for rollback.
- The container rebuild applied 16 available distribution updates; Python dependencies resolved
  within the existing supported ranges, including MCP 2.3.0. No new user permissions were added.
- Local regression suite after the final dependency refresh: 122 passed, 2 skipped. Ruff and
  `pip check` passed; `pip-audit` reported no known vulnerabilities in the checked environment.
- Original local MOV recordings are excluded from Git/source distributions; the previously
  authorized public demo MP4 is preserved.
- Git release version is 0.3.2; the existing directory package uses 1.0.1 after its previous 1.0.0.
- Release commit `e546876ab920094c2fd70596dae7f14a6c222e63` and tag `v0.3.2` are pushed.
- [CI](https://github.com/v4t0r/nextcloud-chatgpt-bridge/actions/runs/39071383019) passed, including
  Python 3.11–3.14, package checks and the Docker deployment smoke test.
- [Release workflow](https://github.com/v4t0r/nextcloud-chatgpt-bridge/actions/runs/39071383080)
  passed. The [published GitHub release](https://github.com/v4t0r/nextcloud-chatgpt-bridge/releases/tag/v0.3.2)
  contains wheel, source archive, directory ZIP 1.0.1 and SHA256SUMS.

## OpenAI portal: submission blocked, not published

Existing identity: `plugin_asdk_app_6a91e995840081918f48e8cd5d8cefff`.
Existing package: `app-6a91e995840081918f48e8cd5d8cefff`.

The current management portal shows **Changes required**, **Not published**, and MCP
**Configuration unavailable**. Endpoint and authentication are unavailable, and Rescan is disabled.
The inspected UI exposes no Connect/Reconnect action. The historical editor still displays the
correct MCP endpoint, predefined OAuth settings and tool definitions, but identifies the version
as rejected and disables editing. The reason for the missing configuration is unknown.

The downloaded 1.0.0 release ZIP contains only `.codex-plugin/plugin.json` listing metadata.
`scripts/build_submission.py` now produces a deterministic, allowlisted package containing
`plugin.json`, `mcp.json`, the workspace skill and icon. It preserves the existing package identity
and contains public OAuth metadata only; no client secret or local credentials.

Both the plugin-specific update dialog and the global Upload Plugin dialog reject this ZIP with:

> Keep the existing MCP connection
> Configure the existing MCP app before updating its plugin ZIP.

No replacement draft was created, no new submission was accepted, and no duplicate app was created.
Successful production tests do not prove that OpenAI's internal review or migration state is correct,
nor do they prove that every possible application defect is absent.

Additional packaging caveat: root `plugin.json` passes the published Agent Plugins JSON schema.
The current generic `mcp.schema.json` rejects server-level `extensions`, while OpenAI's package
documentation explicitly prescribes `mcpServers.<name>.extensions.com.openai.auth` and includes it
in its registered-client example. The package follows that documented OAuth layout; full generic
schema compliance is therefore not claimed. The observed portal rejection concerns the existing
MCP association, not a reported OAuth-extension validation error.

## Support follow-up sent on 2026-10-19

Existing case **16174031** is visible in authenticated support history. Its latest text requests
the annotations for three write tools. The composer says “Create a new case to receive support”.
The attempted new-case action was blocked by automatic approval review because the prior conditional
support authorization did not clearly cover creation of a new case. The user explicitly approved
this new case on 2026-10-19. The message below was then sent through the authenticated OpenAI Help
Center chat and was visibly present in the conversation as a user message. It contains no credentials
or private Nextcloud data. The AI-assisted support responder replied with four clarification
questions. We answered them in the same conversation: this is a public developer-platform directory
submission, not a workspace connector; the exact RBAC role has not been reverified; the affected
management URL and disabled controls were identified; the exact ZIP finding text was confirmed.
We requested specialist escalation and explicitly avoided claiming an unverified owner/admin role.
A new case number and a specialist escalation are not yet confirmed.
The management portal was reloaded on 2026-10-19 and still showed Not published / Changes required /
Configuration unavailable with Rescan disabled. No duplicate initial message was sent.

### Technical support message

Subject: Follow-up to 16174031: existing MCP configuration unavailable prevents resubmission

Please link this request to case 16174031 for plugin
`plugin_asdk_app_6a91e995840081918f48e8cd5d8cefff`, Nextcloud for ChatGPT & Codex.

On 2026-10-17 (Europe/Berlin), the management portal shows Changes required / Not published.
The MCP page shows Configuration unavailable, Endpoint unavailable and Authentication unavailable;
Rescan is disabled and no Connect/Reconnect action is exposed. The historical rejected-version
editor still displays our correct endpoint, predefined OAuth settings and 25 tools, but is read-only.

Both the existing-plugin update flow and global Upload Plugin reject our complete package 1.0.1,
which preserves the existing package name, with: “Keep the existing MCP connection — Configure the
existing MCP app before updating its plugin ZIP.” No draft is created. Please restore the editable
MCP association or specify the supported resubmission procedure for this existing app.

Our public endpoint https://mcp.ooh.world/mcp is operational. On this date, all 17 production
preflight checks passed, including OAuth discovery, PKCE, domain proof and public legal links.
A fresh reviewer authorization-code flow and authenticated tools/list returned all 25 tools;
list_files returned the three synthetic demo folders. Runtime 0.3.2 is deployed.

Regarding the previous request for annotations: upload_file_base64, move_file and delete_file each
declare readOnlyHint=false, destructiveHint=true, openWorldHint=false. The existing submitted
version already displays these values; these write tools were not marked read-only. They target
the authenticated user's stored private Nextcloud account/root and accept no per-call target host.

We are not asserting that the root cause has been proven to be on OpenAI's side. We need an
actionable correction or a working configuration path; current portal controls prevent testing a
new submission. Please route this to the MCP/plugin submission team and identify any actual
remaining reviewer findings. No credentials are included.

References: https://developers.openai.com/plugins/build/plugins and
https://developers.openai.com/plugins/deploy/submission-errors.

## Remaining gates

1. Restore the existing editable MCP association and create the 1.0.1 draft.
2. Scan the live tools, address concrete remaining findings, and verify reviewer access.
3. Complete the portal's required submission confirmations and submit for review.
4. Wait for approval, then publish the approved version. A GitHub release is not store publication.

Operational follow-ups remain: external/off-host backups and complete real two-tenant acceptance.
Future Talk/groupware work is planned in `docs/ROADMAP.md`, not implemented in this release.
