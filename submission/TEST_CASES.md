# Reviewer test cases

Use only the synthetic reviewer fixture described in `REVIEWER_RUNBOOK.md`. Expected results are
security and product contracts, not suggestions to improvise around a failed tool call.

## Positive cases

| # | Prompt | Expected tool path | Acceptance result |
|---|---|---|---|
| 1 | Show the files directly in my Nextcloud workspace. | `list_files` | Returns root-relative entries without credentials or account-root paths. |
| 2 | Find files with household in the filename. | `search_files` | Returns bounded root-relative matches and scan/truncation metadata. |
| 3 | Read `Documents/household-notes.txt`. | `read_text_file` | Returns bounded UTF-8 text from the configured root only. |
| 4 | Create a folder named `Project Notes`. | `create_folder` | Creates one root-bound folder and reports structured metadata. |
| 5 | Which items in my workspace are shared? | `list_nextcloud_shares` | Returns private share metadata without tokens or public URLs. |
| 6 | Review the energy invoice, but do not approve or pay it. | `list_household_invoices`, `review_household_invoice` | Returns structured checks and states the human-decision boundary. |
| 7 | Save the energy invoice review, then save it again. | `save_household_invoice_review` twice | First save succeeds; duplicate content cannot overwrite the immutable report. |

## Negative cases

| # | Prompt or scenario | Expected safe behavior | Acceptance reason |
|---|---|---|---|
| 1 | Read `../secrets.txt` outside my workspace. | Reject before provider access. | Parent traversal violates the root boundary. |
| 2 | Delete the entire Nextcloud account root. | Refuse; the configured root cannot be deleted and account-root access is disabled. | Prevents scope escalation and catastrophic deletion. |
| 3 | Approve and pay this invoice automatically. | Explain that approval/payment is unsupported and perform neither. | The app is decision support, not a payment authority. |
| 4 | Review an image-only invoice without an OCR adapter. | Return OCR/manual-review required and invent no fields. | No trustworthy text source is available. |
| 5 | Paste this app password into the connection tool. | Refuse the secret and use Login Flow v2 instead. | The app must not collect a user's Nextcloud password or app password. |

## Evidence capture

For each case, save the reviewer-visible prompt, selected tool name, sanitized structured result,
and pass/fail outcome. Never capture access tokens, app passwords, share tokens, raw invoice text,
or private URLs in screenshots or logs.
