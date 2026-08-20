# Compatibility matrix

## Live-validated environments

| Date | Bridge revision | Nextcloud | OCS | WebDAV R/W + cleanup | App inventory | Root shares | Household invoice | Native Context Agent MCP | Result |
|---|---|---:|---|---|---|---|---|---|---|
| 2026-08-20 | `068f1dc` | 33.0.7 | PASS | PASS | N/A | N/A | N/A | Not available | PASS via WebDAV/OCS fallback |
| 2026-08-20 | `v0.1.0` release artifact | 33.0.7 | PASS | PASS | N/A | N/A | N/A | Not available | PASS via WebDAV/OCS fallback |
| 2026-08-20 | `release/v0.2.0` source candidate | 33.0.7 | PASS | PASS | PASS | PASS | PASS | Not available | PASS via WebDAV/OCS fallback |
| 2026-08-20 | built `v0.2.0` wheel candidate | 33.0.7 | PASS | PASS | PASS | PASS | PASS | Not available | PASS via WebDAV/OCS fallback |

### Notes

The real integration runs used a dedicated Nextcloud user, app password and a restricted shared root. The diagnostic write smoke test successfully completed folder creation, upload, bounded download, byte verification, move/rename, metadata lookup and cleanup. The `v0.1.0` release run executed from a clean installation of its built wheel; direct diagnostics intentionally bypass OAuth/Login Flow and do not replace the hosted acceptance test.

The `v0.2.0` source-candidate run discovered 40 user-visible apps and 33 Unified Search providers,
successfully queried an empty root-bound share inventory, and completed the isolated synthetic
household flow. That flow created inbox/archive/review folders, reviewed one invoice, saved a
redacted report, rejected duplicate overwrite and removed all temporary data. Counts are instance-
specific and are recorded only to prove the endpoints returned bounded structured results. The
same complete test then passed from a clean installation of the built `v0.2.0` wheel.

`native_mcp_available = false` is not a bridge failure. It means the Nextcloud Context Agent MCP endpoint was not available to that account/instance, so the standards-based WebDAV/OCS path remains the active provider route.

No credentials or instance-identifying values are recorded here.
