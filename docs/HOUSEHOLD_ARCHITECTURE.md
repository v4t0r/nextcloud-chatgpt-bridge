# Household and invoice architecture

## Purpose

The household module adds a tenant-safe decision-support workflow without turning the bridge into
an accounting or payment system. It keeps bridge identity, Nextcloud credentials, profile metadata
and invoice documents in separate trust domains.

```text
Verified OAuth token
       |
       v
BridgeSessionContext (issuer + subject -> tenant_id)
       |
       v
HouseholdService
       |-- HouseholdProfileStore (non-secret metadata)
       |-- ConnectionSettingsProvider (owned connection lookup)
       |-- InvoiceReviewer (bounded local extraction/checks)
       `-- WebDAVClient (root-bound files and immutable reports)
```

## Data separation

| Data | Location | Security property |
|---|---|---|
| Bridge identity | Verified request context | Never contains Nextcloud credentials |
| Connection metadata | Tenant-scoped store | Contains only opaque credential reference |
| Nextcloud app password | Credential store | Encrypted and looked up by tenant + reference |
| Household profile | Tenant-scoped profile store | Paths/currency only; no document content |
| Invoice file | User's Nextcloud workspace | Never copied into the profile database |
| Review report | User's Nextcloud workspace | Redacted JSON, immutable by file SHA-256 |

Every profile operation first resolves the profile with the current `tenant_id`, then resolves the
profile's connection through the same request context. Neither `tenant_id` nor credential reference
is accepted as MCP tool input. Hosted PostgreSQL additionally enforces the tenant/connection pair
with a composite foreign key and cascades profile metadata deletion on disconnect.

## Workspace model

A profile defines three distinct root-relative folders:

- invoice inbox
- invoice archive
- review reports

`prepare_household_workspace` creates only missing path segments and is idempotent. It never moves
existing files or changes folder permissions. The archive path is reserved for future explicitly
confirmed workflows; `v0.2.0` performs no automatic archive operation.

## Invoice review flow

1. List direct supported files in the configured inbox.
2. Reject directories, unsupported extensions and files above the connection transfer limit.
3. Revalidate that the requested path remains inside the inbox.
4. Inspect metadata before bounded download.
5. Extract PDF text with `pypdf`, decode UTF-8 text, or parse supported XML locally.
6. Mark images, encrypted PDFs and scanned PDFs for manual/OCR review instead of guessing.
7. Extract bounded fields and run explicit amount, date, currency and required-field checks.
8. Return structured data without raw extracted text or a full IBAN.
9. Optionally save one immutable report at `<review-path>/<sha256>.review.json`.
10. Treat an existing hash as a duplicate requiring human attention; never overwrite it.

The status `ready_for_human_review` means only that the local checks produced enough structured
data for a person to review. It is not approval. No module can approve, book, pay, transmit or
automatically archive an invoice.

## Supported extraction

- text-bearing PDF, maximum 100 pages
- UTF-8 text, Markdown, CSV and JSON
- XML with conservative UBL/CII-style local-name extraction
- maximum 200,000 extracted characters
- maximum file size inherited from `NEXTCLOUD_MAX_TRANSFER_BYTES`

Image OCR and vision are intentionally absent from the core release. The `InvoiceTextExtractor`
protocol is the extension point for a future adapter. Any remote adapter must receive explicit
deployment configuration, minimize transferred data, document retention, avoid logging content and
return the same bounded `ExtractedDocument` contract.

## Optional OpenAI integration

The provider core does not require an OpenAI API key. When ChatGPT or Codex invokes the published
MCP plugin, the host model can reason over already-redacted structured tool results without the
bridge calling the OpenAI API itself.

An optional OCR/vision or native Nextcloud app that calls the OpenAI API should remain a separate
adapter/service or linked repository. This keeps API billing, model selection, consent, data
retention and key management outside the credential-neutral bridge core while reusing its MCP,
tenant, provider and invoice contracts.
