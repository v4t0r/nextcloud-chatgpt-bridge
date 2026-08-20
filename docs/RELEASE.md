# Release process

Releases are built from a clean `main` commit and published by the tag-triggered GitHub Actions
workflow. The repository remains the source of truth; release artifacts are immutable outputs.

## Preconditions

- version values in `pyproject.toml` and `nextcloud_chatgpt_bridge.__version__` match
- `CHANGELOG.md` and `docs/releases/vX.Y.Z.md` describe the release
- CI passes on every supported Python version
- hosted dependencies and the complete public-app test suite pass
- Codex plugin manifest, assets, skill front matter, and marketplace entry validate
- production Compose configuration, container build, migration, readiness, and egress smoke pass
- package build and `twine check` pass
- dependency audit contains no known runtime vulnerabilities
- live diagnostics pass against a supported Nextcloud instance
- `--v020-test` passes app inventory, root shares, household report redaction and cleanup for v0.2+
- no credential, `.env`, token or private endpoint is present in the diff
- Git history and release artifacts pass the secret scan
- public listing copy and tool annotations match the hosted server contract

## Publish

1. Merge the release pull request into `main`.
2. Create an annotated `vX.Y.Z` tag on the verified merge commit.
3. Push only that tag.
4. The `Release` workflow verifies the version, reruns tests, builds wheel and source archive,
   creates `SHA256SUMS`, verifies a clean wheel installation and publishes the GitHub release.
5. Verify the release page and downloaded checksums before announcing the source release.
6. Save and deploy the exact validated landing-site source as a separate Sites version.
7. Run `nextcloud-chatgpt-preflight` only after the exact production MCP, OAuth, website, support,
   privacy, and terms URLs exist.
8. Treat OpenAI review submission and directory publication as separate owner-controlled actions.

Use `nextcloud-chatgpt-schema --list` to inspect packaged migrations and
`nextcloud-chatgpt-schema --apply` as an explicit operator action. It reads the current PostgreSQL
schema version and applies only pending versions in order. Hosted startup refuses an unexpected
version rather than attempting an implicit migration.

Never rebuild or replace assets for an existing tag. Publish a new patch version instead.
