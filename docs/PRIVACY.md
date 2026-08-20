# Privacy model

This document describes the source application's data flows. A public operator must publish its own
controller identity, contact details, hosting and OAuth providers, processing locations, legal bases,
retention periods, subprocessors, and international-transfer safeguards before hosted accounts open.

## Source project and website

The open-source repository does not receive a user's Nextcloud data merely because the software is
downloaded. The project landing page is designed without advertising, behavioral analytics,
non-essential cookies, or a contact form. It is delivered through OpenAI Sites on Cloudflare
infrastructure. GitHub applies its own policies when a visitor follows a GitHub link or interacts
with the repository.

## Hosted bridge data categories

When a user deliberately connects a hosted bridge deployment, that deployment may process:

- verified OAuth issuer, subject, client ID, and scopes needed to establish bridge identity
- a pseudonymous tenant ID derived from issuer and subject
- Nextcloud server URL, generated login-flow state, connection state, login name, and selected root
- a Nextcloud-generated app password stored only in the encrypted credential store
- requested filenames, metadata, bounded file contents, and provider responses needed for a tool call
- optional household profile paths and structured invoice-review results
- minimal operational events needed for security, reliability, abuse prevention, and deletion

The bridge does not ask for the user's Nextcloud password. Credentials, bearer tokens, share tokens,
raw invoice text, and full IBAN values are excluded from model-visible responses.

## Purpose and data flow

Data is processed only to authenticate the bridge user, connect the user's chosen Nextcloud account,
perform the requested root-bound operation, protect the service, and honor disconnect or deletion.
When a user asks ChatGPT or Codex to read or analyze a file, the bounded tool result is returned to
that host and is then governed by the user's agreement with that host. The bridge itself performs no
model training.

## Storage and retention

Connection metadata and encrypted credentials persist until disconnect, deletion, or an
operator-defined inactivity limit. Expired pending flows and old orphaned encrypted secrets are
removed by maintenance. Household review reports are written into the user's bounded Nextcloud
workspace and remain subject to that user's Nextcloud access and retention controls.

Before hosted accounts open, the operator must publish concrete retention periods for metadata, logs,
backups, inactive accounts, and financial review data. Backups must age out deletions on a documented
schedule.

## Sharing and subprocessors

The core data path includes the user's ChatGPT/Codex host, the bridge operator, the operator's OAuth
provider and hosting infrastructure, and the user's chosen Nextcloud service. No sale of personal
data or advertising use is part of the bridge design. The operator must identify actual subprocessors
and cross-border transfer safeguards before processing public accounts.

## User controls

The application exposes connection status, root selection, and disconnect. Disconnect removes local
connection metadata and encrypted credentials and attempts to revoke the generated Nextcloud app
password. Users can also revoke that app password directly in Nextcloud.

The public operator must provide a verified channel for access, correction, export, objection,
restriction, and deletion requests, plus the applicable supervisory-authority complaint process.

## Security

Tenant predicates, AES-256-GCM credential storage, root enforcement, HTTPS, outbound destination
validation, rate limits, request limits, and secret-minimizing responses reduce risk but do not make
any internet service risk-free. See [`SECURITY.md`](../SECURITY.md).

## Launch blocker

Do not replace the missing public-controller, provider, retention, or transfer details with invented
values. Hosted account connection remains disabled until the real operator completes and publishes
them.
