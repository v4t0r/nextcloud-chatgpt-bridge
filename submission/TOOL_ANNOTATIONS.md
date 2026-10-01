# Production tool annotations

Established connections operate against the authenticated user's bounded private Nextcloud account
and workspace root, so their tools use `openWorldHint=false`. They use the server stored in that
owned connection; file paths cannot select a different host or escape the configured root. The
tools do not browse the public web, create public shares, or send content to arbitrary recipients.
Capability discovery is restricted to the same authenticated account's server and permissions.
Disconnect revokes only that owned account's app password at its stored server. Metadata-only
connection and household-profile tools operate on owned bridge records.

Starting and polling Login Flow v2 can contact a user-specified Nextcloud host, so those two tools
use `openWorldHint=true`. A write can still be destructive inside a private workspace.

This follows the [OpenAI annotation guidance](https://developers.openai.com/plugins/reference#annotations):
external hosting alone does not make a bounded private account open-world. The 2026-09-30 automated
review nevertheless flagged 13 tools for external-system access and held six others for further
review. The descriptions now state the private-account boundary explicitly; annotation booleans,
tool schemas, authorization, and root enforcement remain unchanged.

| Tool | Read only | Destructive | Idempotent | Rationale |
|---|---:|---:|---:|---|
| `get_nextcloud_capabilities` | yes | no | n/a | Reads server capabilities. |
| `get_nextcloud_app_accesses` | yes | no | n/a | Reads user-visible app inventory. |
| `probe_native_nextcloud_mcp` | yes | no | n/a | Performs discovery only. |
| `list_files` | yes | no | n/a | Lists root-bound entries. |
| `search_files` | yes | no | n/a | Searches filenames below the root. |
| `list_nextcloud_shares` | yes | no | n/a | Reads redacted private-share metadata. |
| `get_file_info` | yes | no | n/a | Reads one item's metadata. |
| `read_text_file` | yes | no | n/a | Reads bounded text. |
| `download_file_base64` | yes | no | n/a | Reads bounded binary content. |
| `write_text_file` | no | yes | no | May create or overwrite file content. |
| `upload_file_base64` | no | yes | no | May create or overwrite binary content. |
| `create_folder` | no | no | no | Creates private workspace state. |
| `move_file` | no | yes | no | Renames/moves an existing item. |
| `delete_file` | no | yes | yes | Repeating the same deletion has no additional effect. |
| `begin_nextcloud_connection` | no | no | no | Creates a short-lived Login Flow. |
| `poll_nextcloud_connection` | no | no | no | Polling may consume credentials and finalize a connection. |
| `list_nextcloud_connections` | yes | no | n/a | Lists credential-free owned metadata. |
| `set_nextcloud_root` | no | no | yes | Repeating the same root assignment is stable. |
| `disconnect_nextcloud` | no | yes | no | Deletes bridge state and attempts credential revocation. |
| `configure_household_account` | no | no | yes | Upserts non-secret profile metadata. |
| `list_household_accounts` | yes | no | n/a | Lists owned profile metadata. |
| `prepare_household_workspace` | no | no | yes | Creates only missing folders. |
| `list_household_invoices` | yes | no | n/a | Lists bounded inbox candidates. |
| `review_household_invoice` | yes | no | n/a | Extracts checks without changing the invoice. |
| `save_household_invoice_review` | no | no | yes | Content hash prevents duplicate overwrite. |

The automated hosted-tool contract test requires every public tool to have a title, description,
input schema, output schema, and explicit boolean values for read-only, destructive, and
open-world annotations. It also locks the expected production tool set and idempotency choices.
