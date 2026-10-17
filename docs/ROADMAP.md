# Roadmap

The roadmap keeps the standards-based Nextcloud core independent from any one AI provider while
progressively preparing a universal public plugin for ChatGPT and Codex.

## v0.2.0 — household foundation

- tenant-scoped household profiles bound to owned Nextcloud connections
- idempotent inbox/archive/review workspace setup
- bounded PDF, text and XML invoice review
- immutable redacted review reports and duplicate hash detection
- user-visible app and search-provider inventory
- root-bound filename search and read-only share inventory
- PostgreSQL household metadata migration and automated isolation tests
- real Nextcloud 33.0.7 acceptance test with isolated temporary data

## Deferred review quality and controlled writes

- optional OCR/vision adapter behind the existing extractor protocol
- explicit consent, minimization and retention contract for remote document processing
- stronger ZUGFeRD, XRechnung, UBL and CII field/check coverage
- confidence/provenance fields for every extracted invoice value
- duplicate and supplier-history heuristics without automatic financial decisions
- optionally confirmed share create/update/revoke workflows with exact destructive annotations
- expanded malformed-document, parser-resource and redaction tests

No future feature may approve, book or pay an invoice without a separate product and security
decision. The current public app intentionally exposes no payment authority.

## v0.3.0 — public app release candidate

- production-facing OAuth-protected universal MCP application
- exact request-scoped tenant identity and encrypted credential separation
- DNS-rebinding-resistant outbound HTTPS proxy and isolated network composition
- trusted-host, origin, request-size, security-header, and rate-limit controls
- explicit database migration, readiness, and maintenance processes
- stable schemas and complete review annotations for every hosted tool
- release preflight for MCP health, resource metadata, OAuth, legal URLs, and domain challenge
- Codex plugin package, listing copy, reviewer cases, and public landing-site source

## v0.3.1 — public launch and review operations

- deploy the universal MCP endpoint and preserve the reference network boundary
- configure external OAuth/OIDC and validate exact client-registration behavior
- complete legal pages with the actual hosting and identity providers
- document retention, deletion, backups, restore, key operations, monitoring, and incident response
- create a disposable reviewer identity and synthetic Nextcloud fixture
- complete end-to-end ChatGPT and Codex acceptance
- submit for OpenAI review, remediate findings, and publish only after approval

## v0.3.2 — submission recovery (2026-10-17)

- Restore a complete portable directory package with `mcp.json`, fixed OAuth client metadata,
  verified publisher metadata, legal links, logo and workspace skill.
- Preserve the existing directory package name; directory version 1.0.1 is separate from runtime
  0.3.2. Upload, successful scan, submission, approval and publication are distinct gates.
- Refresh dependency/security checks and explicitly validate the OAuth resource in the MCP SDK.
- First finish the current Files/invoice submission. Do not mix unfinished provider features into it.

## v0.4 — Talk and provider foundation

1. Introduce a provider registry with app/API capabilities, version checks and explicit connection
   selection. Continue using tenant-owned encrypted Nextcloud Login Flow credentials.
2. Add opt-in, tenant-scoped resource grants: selected Talk conversations, later calendars,
   address books and boards. A Files workspace root does not authorize these other applications.
3. Implement bounded `list_talk_conversations` and `read_talk_messages`, with pagination, message
   limits and minimized metadata. Treat messages and attachments as untrusted data.
4. Read chat history without side effects: `setReadMarker=0`, `noStatusUpdate=1`, and
   `markNotificationsAsRead=0` where the server advertises `chat-keep-notifications`. If side effects
   cannot be prevented on the installed version, do not label that operation read-only.
5. Add a separate send operation only after explicit recipient/conversation and text approval;
   require a bounded conversation grant and handle ambiguous retries without duplicate posting.
   Do not add public-room creation, invitations, calls or federation administration initially.

Acceptance: two real isolated test tenants, forbidden-room and revoked-grant tests, version/capability
fallback tests, pagination/limits, no read-marker changes, send-confirmation and retry tests,
accurate annotations and a fresh OpenAI tool scan. A test proving read-only behavior is required
before advertising `readOnlyHint=true`. No unrestricted REST or `occ` command tool.

## v0.5 — Calendar, Tasks and Contacts

- CalDAV calendars/events and VTODO tasks; CardDAV address books/contacts.
- Explicit selection of collections; minimal field sets, bounded time windows and result counts.
- Separate read/create/update/delete tools with ETag/If-Match conflict protection.
- Test recurrence, all-day events, timezones/DST and malformed iCalendar/vCard content.
- Invitations, attendee changes and notification-producing actions require separate consent and
  annotations; reading or editing an event must not silently email participants.
- Complete per-provider two-tenant and collection-isolation acceptance and review before release.

## v0.6 — Notes and Deck

- Notes through its documented app API; selected notes/categories and bounded content.
- Deck through its documented API; selected boards, stacks and cards, with assignment/notification
  side effects surfaced before writes. Permission-denied and missing-app paths are explicit.
- Add root-scoped file versions/tags only where the upstream API preserves the existing boundary.

## v0.7 and later — Tables, Collectives and additional apps

- Assess Tables and Collectives individually for stable documented APIs and resource permissions.
- Maintain a compatibility matrix of tested Nextcloud/app versions and capabilities. An installed
  app or an `occ` command is not proof that a stable user-level remote API exists.
- Mail, administration, app installation and unrestricted search remain separate design decisions.
- Prefer documented OCS/REST, WebDAV, CalDAV and CardDAV APIs. Do not use database/ODBC access to
  bypass application authorization, and do not expose arbitrary shell/`occ` arguments through MCP.
- If a genuine administration feature is required later, design a separate local administrator
  service with an explicit command allowlist, audit trail and permissions; never bundle it with
  the public user-level bridge by default.

### Sources checked on 2026-10-17

- [Talk chat API](https://nextcloud-talk.readthedocs.io/en/stable/chat/)
- [Nextcloud OCS API overview](https://docs.nextcloud.com/server/stable/developer_manual/client_apis/OCS/ocs-api-overview.html)
- [DAV and database administration commands](https://docs.nextcloud.com/server/stable/admin_manual/occ_database.html)
- [OpenAI package format](https://developers.openai.com/plugins/build/plugins)

The public documentation currently targets newer Nextcloud releases; actual support must be
verified against the user's installed app versions. These releases are planned, not implemented.

## Native Nextcloud app / OpenAI API track

A native Nextcloud administration or assistant app may later reuse this bridge through its stable
interfaces. It should be developed as a linked repository or separately deployed adapter unless a
future design review proves that in-process integration materially improves security and operations.
The separation avoids embedding OpenAI API keys, model policy and billing concerns in the reusable
WebDAV/OCS/MCP core.

Architecture or repository-boundary changes that weaken tenant isolation, root scope or credential
separation require an explicit security review before implementation.
