# OpenAI listing copy

This file is the canonical copy deck for the OpenAI submission form. Known production website
URLs are recorded below; bridge and OAuth values remain release gates until their deployments exist.

## Product

- **Name:** Nextcloud for ChatGPT & Codex
- **Developer:** v4t0r
- **Category:** Productivity
- **Authentication:** OAuth 2.1 at the bridge; Nextcloud Login Flow v2 for account connection

## Short description

Work safely with files in your own Nextcloud workspace.

## Long description

Connect your own Nextcloud account to ChatGPT and Codex without sharing your Nextcloud password.
Browse, search, read, organize, upload, and review files inside a workspace root you control. Each
user and tenant is isolated, bridge identity stays separate from encrypted Nextcloud credentials,
and household invoice checks remain conservative decision support: the app never approves, books,
pays, transmits, or automatically archives invoices.

## Starter prompts

1. Show the files at the top level of my Nextcloud workspace.
2. Find documents with “household” in the filename.
3. Summarize this text file from my Nextcloud workspace.
4. Create a folder named `Project Notes` in my workspace.
5. Review the newest household invoice, but do not approve or pay it.

## Required public fields

Use these exact website URLs:

- **Product website:** https://nextcloud-for-chatgpt.v4t0r.chatgpt.site
- **Support:** https://nextcloud-for-chatgpt.v4t0r.chatgpt.site/support
- **Privacy policy:** https://nextcloud-for-chatgpt.v4t0r.chatgpt.site/privacy
- **Terms of service:** https://nextcloud-for-chatgpt.v4t0r.chatgpt.site/terms

Fill these only from the deployed bridge environment immediately before submission:

- production MCP URL
- verified MCP domain
- OAuth discovery and client-registration details

Do not substitute preview, localhost, private-network, placeholder, or repository-only URLs.
