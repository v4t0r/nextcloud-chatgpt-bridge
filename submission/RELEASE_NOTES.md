# Submission release notes — v0.3.0

`v0.3.0` is the production-deployment and OpenAI-submission candidate for **Nextcloud for ChatGPT
& Codex**.

## Highlights

- public OAuth-protected Streamable HTTP MCP application
- tenant-isolated bridge identities and encrypted Nextcloud credentials
- Nextcloud Login Flow v2 account connection without password collection
- root-bound WebDAV/OCS file operations and conservative household invoice review
- PostgreSQL migrations, readiness checks, maintenance worker, rate limits, and security headers
- DNS-rebinding-resistant outbound HTTPS proxy and network-isolated production composition
- exact OAuth/resource-metadata/domain-challenge release preflight
- Codex plugin package, reviewer cases, listing copy, and public-site source

## Release boundary

The source release does not by itself activate a hosted service or publish an OpenAI directory
listing. Public production hosting, verified publisher identity, external OAuth configuration, a
synthetic reviewer account, domain verification, OpenAI review, and the owner's deliberate publish
action remain separate operational gates.
