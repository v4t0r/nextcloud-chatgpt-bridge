# OpenAI reviewer runbook

Keep reviewer credentials outside Git and outside release artifacts. The reviewer identity and its
Nextcloud account must be disposable, non-admin, internet-accessible, and usable without MFA, SMS,
email confirmation, VPN, or private-network access.

## Synthetic fixture

Configure one reviewer-owned connection with a dedicated root containing only:

```text
Documents/household-notes.txt
Household/Invoices/Inbox/energy-2026-0042.txt
Household/Invoices/Archive/
Household/Invoices/Reviews/
Shared/reviewer-example.txt
```

Use fictional names, addresses, invoice numbers, bank data, and amounts. Include one private
user/group share for `Shared/reviewer-example.txt`; do not create a public-link share.

## Before submission

1. Run the release preflight against the exact production URLs.
2. Complete every case in `TEST_CASES.md` from both ChatGPT and Codex where available.
3. Verify disconnect/reconnect once with a fresh Login Flow.
4. Confirm privacy, terms, support, website, health, OAuth metadata, and MCP URLs are public.
5. Confirm the reviewer account has no access outside the synthetic root.
6. Store reviewer credentials only in the OpenAI submission form's protected reviewer field.

## Reviewer instructions

1. Sign in with the supplied bridge reviewer identity.
2. The synthetic Nextcloud connection is already available; no Nextcloud administrator access is
   required.
3. Run the listed positive and negative prompts.
4. The app may ask for confirmation before destructive changes. This is expected.
5. Report any path escape, cross-user data, secret exposure, unrequested write, or invented invoice
   field as a release-blocking failure.

## After review

Revoke the bridge reviewer session, disconnect the synthetic Nextcloud connection, revoke the
generated app password, rotate submission credentials, and remove any captured test artifacts.
