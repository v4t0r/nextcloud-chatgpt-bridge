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

## v0.2.1 — review quality and controlled writes

- optional OCR/vision adapter behind the existing extractor protocol
- explicit consent, minimization and retention contract for remote document processing
- stronger ZUGFeRD, XRechnung, UBL and CII field/check coverage
- confidence/provenance fields for every extracted invoice value
- duplicate and supplier-history heuristics without automatic financial decisions
- optionally confirmed share create/update/revoke workflows with exact destructive annotations
- expanded malformed-document, parser-resource and redaction tests

No `v0.2.1` feature may approve, book or pay an invoice.

## v0.3.0 — Nextcloud app providers

- CalDAV calendars and tasks with read/write separation
- CardDAV contacts with minimized response fields
- provider interfaces for Talk, Deck, Notes, Collectives and Tables
- tags and file-version metadata where root scope can be enforced
- explicit capability negotiation between native Nextcloud MCP and standards/API fallbacks
- connection selection for tenants with multiple active Nextcloud accounts
- stable response schemas and plugin-review metadata for every public tool

## v0.3.x — public plugin operations

- production universal MCP endpoint and verified domain
- external OAuth/OIDC deployment plus UserInfo/openid/email support where needed
- DNS-rebinding-safe egress enforcement, rate limits and abuse controls
- managed key operations, secret-free audit logs, retention/deletion jobs and monitoring
- public website, support, privacy and terms URLs
- reviewer-ready account/fixtures and end-to-end ChatGPT/Codex acceptance
- OpenAI submission, review remediation and publication in the universal Plugins Directory

## Native Nextcloud app / OpenAI API track

A native Nextcloud administration or assistant app may later reuse this bridge through its stable
interfaces. It should be developed as a linked repository or separately deployed adapter unless a
future design review proves that in-process integration materially improves security and operations.
The separation avoids embedding OpenAI API keys, model policy and billing concerns in the reusable
WebDAV/OCS/MCP core.

Architecture or repository-boundary changes that weaken tenant isolation, root scope or credential
separation require an explicit security review before implementation.
