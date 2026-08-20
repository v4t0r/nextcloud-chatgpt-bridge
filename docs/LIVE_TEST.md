# Live Nextcloud validation

This is the acceptance test for the current Files/MCP milestone.

## Test account

Use a dedicated non-admin Nextcloud user where practical. Create an app password in the user's security settings. Do not paste the app password into issues, commits, chat transcripts or command-line arguments.

Create a workspace folder such as `/ChatGPT` and restrict the test user to only the data it actually needs.

## Windows preparation

From the repository checkout:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Read-only acceptance test

```powershell
.\scripts\diagnose-nextcloud.ps1 `
  -BaseUrl "https://cloud.example.com" `
  -Username "chatgpt-bridge" `
  -RootPath "/ChatGPT"
```

The script prompts for the Nextcloud app password as a PowerShell SecureString. The password is placed in a process environment variable only for the diagnostic run and removed in `finally` cleanup.

Expected sanitized JSON properties:

```json
{
  "cleanup_ok": null,
  "failed_stages": [],
  "native_mcp_available": false,
  "native_mcp_protocol": null,
  "native_mcp_tool_count": null,
  "nextcloud_version": "...",
  "ocs_ok": true,
  "root_entries": 0,
  "webdav_ok": true,
  "write_test_ok": null,
  "write_test_requested": false
}
```

`native_mcp_available=false` is not a failure. It simply means Context Agent MCP is not installed/reachable for that user/instance and the bridge will use standards-based fallbacks.

## Explicit write acceptance test

Only after the read-only test succeeds:

```powershell
.\scripts\diagnose-nextcloud.ps1 `
  -BaseUrl "https://cloud.example.com" `
  -Username "chatgpt-bridge" `
  -RootPath "/ChatGPT" `
  -WriteTest
```

The write test operates only inside one randomized folder named like `.bridge-smoke-0123abcdef45` below the configured root. It performs:

1. `MKCOL` temporary folder
2. `PUT` small probe file
3. bounded `GET` and byte-for-byte verification
4. `MOVE` rename
5. `PROPFIND` metadata verification
6. recursive `DELETE` of the temporary folder

Cleanup is attempted in `finally` if an intermediate step fails.

Expected result includes:

```json
{
  "failed_stages": [],
  "ocs_ok": true,
  "webdav_ok": true,
  "write_test_requested": true,
  "write_test_ok": true,
  "cleanup_ok": true
}
```

## Acceptance criteria

The Files/MCP milestone is accepted only when:

- read-only diagnostics exit with code `0`
- OCS capability detection works
- WebDAV root listing works
- the write smoke test completes and cleans up
- no secret appears in output/logs
- an installed Context Agent, if present, can be discovered through its MCP endpoint without invoking a native tool

Only after these checks should the project move on to shares/search, public MCP authentication or CalDAV/CardDAV functionality.
