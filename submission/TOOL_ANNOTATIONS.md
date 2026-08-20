# Production tool annotations

All tools operate against the authenticated user's private Nextcloud system, so
`openWorldHint=false` throughout. A write can still be destructive even though it is closed-world.

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
