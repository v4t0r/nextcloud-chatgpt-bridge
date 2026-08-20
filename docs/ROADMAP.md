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

## v0.4 — broader Nextcloud providers

- CalDAV calendars and tasks with read/write separation
- CardDAV contacts with minimized response fields
- provider interfaces for Talk, Deck, Notes, Collectives, and Tables
- tags and file-version metadata where root scope can be enforced
- explicit capability negotiation between native Nextcloud MCP and standards/API fallbacks
- explicit connection selection for tenants with multiple active Nextcloud accounts

## Native Nextcloud app / OpenAI API track

A native Nextcloud administration or assistant app may later reuse this bridge through its stable
interfaces. It should be developed as a linked repository or separately deployed adapter unless a
future design review proves that in-process integration materially improves security and operations.
The separation avoids embedding OpenAI API keys, model policy and billing concerns in the reusable
WebDAV/OCS/MCP core.

Architecture or repository-boundary changes that weaken tenant isolation, root scope or credential
separation require an explicit security review before implementation.
