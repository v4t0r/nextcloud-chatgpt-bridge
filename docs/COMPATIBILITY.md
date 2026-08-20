# Compatibility matrix

## Live-validated environments

| Date | Bridge revision | Nextcloud | OCS | WebDAV read | WebDAV write smoke | Cleanup | Native Context Agent MCP | Result |
|---|---|---:|---|---|---|---|---|---|
| 2026-08-20 | `068f1dc` | 33.0.7 | PASS | PASS | PASS | PASS | Not available | PASS via WebDAV/OCS fallback |
| 2026-08-20 | `v0.1.0` release artifact | 33.0.7 | PASS | PASS | PASS | PASS | Not available | PASS via WebDAV/OCS fallback |

### Notes

The real integration runs used a dedicated Nextcloud user, app password and a restricted shared root. The diagnostic write smoke test successfully completed folder creation, upload, bounded download, byte verification, move/rename, metadata lookup and cleanup. The release run executed from a clean installation of the built `v0.1.0` wheel; direct diagnostics intentionally bypass OAuth/Login Flow and do not replace the hosted acceptance test.

`native_mcp_available = false` is not a bridge failure. It means the Nextcloud Context Agent MCP endpoint was not available to that account/instance, so the standards-based WebDAV/OCS path remains the active provider route.

No credentials or instance-identifying values are recorded here.
