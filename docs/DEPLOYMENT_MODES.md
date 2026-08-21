# Deployment modes

The bridge does not depend on publication in the OpenAI plugin directory. Publication controls
distribution and discovery; it does not activate the MCP server or its Nextcloud providers.

## Private direct MCP

Use this mode for one operator or a small trusted environment.

- Codex CLI, the ChatGPT desktop app, and the Codex IDE extension can start the bridge directly as
  an MCP stdio process.
- The same clients can connect to a private Streamable HTTP endpoint.
- ChatGPT developer mode can connect through a public HTTPS endpoint or Secure MCP Tunnel when the
  account and workspace expose that feature.
- Secure MCP Tunnel keeps the server private, but OpenAI documents it as a development/private
  connection mechanism, not as a replacement for the public endpoint required for submission.

This mode uses the local `.env` contract and one dedicated Nextcloud app password. It is not the
multi-user hosted identity model.

```bash
cp .env.example .env
python -m venv .venv
pip install -e ".[dev]"
nextcloud-chatgpt-bridge
```

Register the installed stdio command with Codex:

```bash
codex mcp add nextcloud -- nextcloud-chatgpt-bridge
```

The command must run with the repository as its working directory so the untracked `.env` file can
be read. Alternatively, provide the four `NEXTCLOUD_*` values through the host's secret-aware
environment configuration. Never put an app password in a committed MCP configuration file.

Official references:

- [Codex and ChatGPT desktop MCP configuration](https://learn.chatgpt.com/docs/extend/mcp)
- [Connect and test an unpublished MCP server](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)

## Public multi-user MCP

Use this mode when unrelated users connect their own Nextcloud accounts.

The reference composition in `deploy/compose.production.yml` provides PostgreSQL, encrypted
credential storage, migrations, cleanup, an outbound-only Nextcloud egress boundary, the stateless
MCP application, and Caddy TLS termination. It requires:

- a stable public DNS name and HTTPS reachability
- an external OAuth/OIDC authorization server
- deployment-host secret files and off-host backups
- monitoring, retention, deletion, and incident-response operations

The service can be used by compatible MCP hosts before any directory publication. ChatGPT web
availability still depends on developer-mode access or an installed published plugin. Store
publication remains necessary only for general ChatGPT directory distribution.

## OpenAI API boundary

The bridge does not call an OpenAI model API. Secure MCP Tunnel separately requires a runtime API
key for its control-plane connection according to OpenAI's documentation. The repository does not
create, store, or require that key for direct stdio or public HTTPS operation.
