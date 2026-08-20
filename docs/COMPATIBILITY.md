# Compatibility matrix

## Live-validated environments

| Date | Nextcloud | OCS | WebDAV read | WebDAV write smoke | Cleanup | Native Context Agent MCP | Result |
|---|---:|---|---|---|---|---|---|
| 2026-08-20 | 33.0.7 | PASS | PASS | PASS | PASS | Not available | PASS via WebDAV/OCS fallback |

### Notes

The first real integration run used a dedicated Nextcloud user, app password and a restricted shared root. The diagnostic write smoke test successfully completed folder creation, upload, bounded download, byte verification, move/rename, metadata lookup and cleanup.

`native_mcp_available = false` is not a bridge failure. It means the Nextcloud Context Agent MCP endpoint was not available to that account/instance, so the standards-based WebDAV/OCS path remains the active provider route.

No credentials or instance-identifying values are recorded here.
