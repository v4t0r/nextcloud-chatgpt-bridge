# Release process

Releases are built from a clean `main` commit and published by the tag-triggered GitHub Actions
workflow. The repository remains the source of truth; release artifacts are immutable outputs.

## Preconditions

- version values in `pyproject.toml` and `nextcloud_chatgpt_bridge.__version__` match
- `CHANGELOG.md` and `docs/releases/vX.Y.Z.md` describe the release
- CI passes on every supported Python version
- package build and `twine check` pass
- dependency audit contains no known runtime vulnerabilities
- live diagnostics pass against a supported Nextcloud instance
- no credential, `.env`, token or private endpoint is present in the diff

## Publish

1. Merge the release pull request into `main`.
2. Create an annotated `vX.Y.Z` tag on the verified merge commit.
3. Push only that tag.
4. The `Release` workflow verifies the version, reruns tests, builds wheel and source archive,
   creates `SHA256SUMS`, verifies a clean wheel installation and publishes the GitHub release.
5. Verify the release page and downloaded checksums before announcing the release.

Never rebuild or replace assets for an existing tag. Publish a new patch version instead.
