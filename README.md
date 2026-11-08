# Maximo MCP Server

[![npm version](https://img.shields.io/npm/v/@soumyaprasadrana/maximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/%40soumyaprasadrana%2Fmaximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![Node.js](https://img.shields.io/badge/node-%3E%3D20-339933.svg)](https://nodejs.org)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://soumyaprasadrana.github.io/maximo-mcp-server)

**Give AI agents safe, governed access to IBM Maximo.**

Agents look up the schema before they query, stage every change, show a diff, and write to Maximo
only after a human says yes. Works with Claude, Cursor, Copilot Studio, watsonx Orchestrate and any
MCP client -- over stdio or HTTP.

```bash
npm install -g @soumyaprasadrana/maximo-mcp-server
```

[Documentation](https://soumyaprasadrana.github.io/maximo-mcp-server) -
[Quick start](#quick-start) -
[What agents can do](#what-agents-can-do) -
[Configuration](#configuration) -
[Changelog](CHANGELOG.md)

---

## What it looks like

> **User:** Which work orders at BEDFORD are waiting for approval, and approve the ones for pump 11430.
>
> The agent, through this server:
> 1. `maximo_aggregate` -- 1,284 work orders in WAPPR; 37 at BEDFORD.
> 2. `os_query_builder` + `ws_load` -- loads the 3 for asset 11430.
> 3. `maximo_plan_status_change` -- WAPPR -> APPR is a valid next status; nothing changed yet.
> 4. Shows you the plan. **You:** "yes".
> 5. `maximo_change_status` -- done, with your memo, under Maximo's own rules and signatures.

Every write goes through the same pattern: **look up -> stage -> preview -> confirm -> commit**.

---

## Quick start

**1. Prerequisites.** Node.js 20+, network access to Maximo, and a Maximo API key.

**2. Deploy one automation script in Maximo** (once). The server reads Maximo's metadata through it.

- Name: `MAXMCPMETADATA` -- source:
  `https://raw.githubusercontent.com/soumyaprasadrana/maximo-mcp-server/refs/heads/main/MAXMCPMETADATA.py`
- Maximo: System Configuration -> Platform Configuration -> Automation Scripts -> create a script
  with that name, paste the source, activate it.

**3. Add it to your MCP client.** Claude Desktop (`claude_desktop_config.json`), Cursor and Claude
Code use the same shape:

```json
{
  "mcpServers": {
    "maximo": {
      "command": "maximo-mcp-server",
      "env": {
        "MAXIMO_URL": "https://your-maximo-host/maximo",
        "MAXIMO_API_KEY": "your-api-key",
        "MCP_DATA_BASE_DIR": "/opt/maximo-mcp",
        "MCP_LOGS_DIR": "/opt/maximo-mcp/logs",
        "MCP_RECONCILE_LAZY": "true"
      }
    }
  }
}
```

`MCP_RECONCILE_LAZY` makes the server ready in seconds and fetches each object structure's
metadata the first time it is needed. Restart the client after installing or upgrading -- clients
cache the tool list.

---

## Pick your setup

| You want | Add |
|---|---|
| One user in Claude / Cursor / Claude Code | nothing more |
| Q&A and reporting with no way to change data | `--readonly` |
| A shared server for many users over the network | `--transport http --port 8001` + [OAuth](#http-and-oauth) |
| Each user to act as themselves in Maximo | `--transport http --caller-apikey` |
| Staged changes that survive a server restart | `--ws-persist` |
| watsonx Orchestrate or Copilot Studio (strict schema importers) | `--strict-tool-schema` |
| A coding agent configuring Maximo (dev environments) | `--copilot-mode` |
| Everything above, minus specific tools | `--disabled-tools "maximo_import_file*,ws_commit*"` |

Every flag also has an environment variable -- see [Configuration](#configuration) or
`maximo-mcp-server --help`.

---

## What agents can do

**Find and read** -- *read-only, also on `--readonly`*
- Search object structures, fields and relationships (`maximo_get_metadata`).
- Build validated queries with filters, child rows, timelines, saved queries and KPIs
  (`os_query_builder`), load and page through records (`ws_load`, `ws_next_page`).
- Count, sum and average per group, computed by Maximo (`maximo_aggregate`).
- Get the valid values for any field -- assets, locations, work types, crews, statuses
  (`maximo_lookup_values`).
- Run BIRT reports and get the PDF (`maximo_list_reports`, `maximo_run_report`).
- Read attachments, any Maximo URL (same host, GET only), integration errors and -- opt-in -- the
  Maximo server log.

**Change data, safely**
- Create, update and delete records in a **working set**: every change is staged and previewed
  with validation warnings before `ws_commit` writes it.
- Add or remove child rows, attach files (`ws_add_attachment`).
- Change statuses with a plan-then-confirm step, checked against Maximo's valid next statuses and
  electronic signatures (`maximo_plan_status_change`, `maximo_change_status`).
- Route workflow assignments and start processes (`maximo_complete_workflow_assignment`,
  `maximo_start_workflow`).
- Invoke any allowed action, import CSV/XML files with a preview, run automation scripts.

**Configure Maximo** -- *with `--copilot-mode`, for development environments*
- Configure Database (status, apply, discard), Admin Mode, system properties, read-only SQL,
  live cache reload, App Designer presentation edits -- each with Maximo's own permission checks.

Full tool reference: [docs / tools](https://soumyaprasadrana.github.io/maximo-mcp-server/tools/).

---

## Safe by design

- **Data changes are previewed first.** Working-set commits, status changes, workflow
  routing, attachments and imports all show what will happen and wait for a confirm. The generic
  `maximo_invoke_action` and automation-script tools run at once -- hide them with
  `--disabled-tools` or use `--readonly` if your agents should not have them.
- **Maximo stays the authority.** Allowed actions, valid next statuses, security groups,
  electronic signatures and `BMXAA` errors come from Maximo, verbatim.
- **Your key goes nowhere else.** Every request is pinned to `MAXIMO_URL`; the key travels only in
  a header and never follows a redirect to another host.
- **You choose the surface.** `--readonly` for read paths only, configuration tools only with
  `--copilot-mode`, any tool hidden with `--disabled-tools`.
- **Per-user identity** over HTTP (`--caller-apikey`): each request runs as the user whose API key
  it carries; working sets are private to their creator.
- **Restart-safe** with `--ws-persist`: staged changes survive, and a commit interrupted by a crash
  is never re-sent automatically.

---

## HTTP and OAuth

With `--transport http` every MCP request needs an OAuth 2.0 bearer token (client credentials).

```bash
# 1. create a client (the secret is shown once)
maximo-mcp-server --setup-oauth --data-dir /opt/maximo-mcp --maximo-url https://your-maximo/maximo --maximo-api-key KEY

# 2. get a token at runtime
curl -X POST http://localhost:8001/oauth/token -d "grant_type=client_credentials" -d "client_id=ID" -d "client_secret=SECRET"
```

Send `Authorization: Bearer <token>` on every request. `--list-oauth-clients` and
`--delete-oauth-client <id>` manage clients; secrets are stored hashed. Step-by-step setup for
Claude Desktop, watsonx Orchestrate and other HTTP clients:
[docs / connecting clients](https://soumyaprasadrana.github.io/maximo-mcp-server/guide/clients).

---

## Configuration

Required: `MAXIMO_URL`, `MAXIMO_API_KEY`, `MCP_DATA_BASE_DIR`, `MCP_LOGS_DIR` (or `--maximo-url`,
`--maximo-api-key`, `--data-dir`, `--logs-dir`).

<details>
<summary><b>Transport and identity</b></summary>

| Variable | CLI flag | Default | Description |
|---|---|---|---|
| `MCP_TRANSPORT` | `--transport` | `stdio` | `stdio` or `http` |
| `MCP_SERVER_PORT` | `--port` | `8001` | HTTP port |
| `MCP_SERVER_HOST` | `--host` | all interfaces | HTTP bind address, e.g. `127.0.0.1` |
| `MCP_CALLER_APIKEY` | `--caller-apikey` | `false` | Run each HTTP request as the user whose key is in `x-maximo-apikey` |
| `MCP_STRICT_TOOL_SCHEMA` | `--strict-tool-schema` | `false` | Strict tool schemas (watsonx Orchestrate, Copilot Studio) |
| `MCP_OAUTH_TOKEN_TTL` | `--oauth-token-ttl` | `3600` | Token lifetime in seconds |
| `MAXIMO_ESIG_AUTH` | -- | -- | base64 of the service account's password: status changes are signed for callers, who only give a reason |

</details>

<details>
<summary><b>Which tools are exposed</b></summary>

| Variable | CLI flag | Default | Description |
|---|---|---|---|
| `MCP_READONLY` | `--readonly` | `false` | Read tools only (plus diagnostics) |
| `MCP_ENABLE_SCRIPT_GET` | `--enable-script-get` | `false` | With `--readonly`, a GET-only automation-script tool |
| `MCP_COPILOT_MODE` | `--copilot-mode` | `false` | Configuration tools and Migration Manager object structures |
| `MCP_DISABLED_TOOLS` | `--disabled-tools` | -- | Tools never to register; trailing `*` = prefix; unmatched entries are reported |
| `MCP_ENABLE_SERVER_LOGS` | `--enable-server-logs` | `false` | `maximo_read_server_log` (Maximo's log holds other users' data) |
| `MCP_ENABLE_DEV_MODE` | `--dev-mode` | `false` | `mcp_read_logs` (`mcp_server_status` is always there) |

</details>

<details>
<summary><b>Metadata</b></summary>

| Variable | CLI flag | Default | Description |
|---|---|---|---|
| `MCP_RECONCILE_LAZY` | `--reconcile-lazy` | `false` | On-demand metadata: ready in seconds, no startup sync (recommended) |
| `MCP_RECONCILE_LAZY_TTL` | `--reconcile-lazy-ttl` | `86400` | Seconds before cached metadata is refetched |
| `MCP_RECONCILE_ON_STARTUP` | `--reconcile-on-startup` | `true` | Full sync at startup (when not lazy) |
| `MCP_RECONCILE_ON_RESTART` | `--force-reconcile` | `false` | Force a full re-sync |
| `MCP_BG_SYNC_WORKER` | `--bg-sync-worker` | `false` | Run the full sync in a background process |
| `MCP_RECONCILE_WEEKLY_ENABLED` | `--reconcile-weekly` | `false` | Weekly refresh (`MCP_RECONCILE_WEEKLY_CRON`) |
| `MCP_EMBEDDINGS_MODE` | `--embeddings-mode` | `none` | `local` adds semantic search; needs `@xenova/transformers` installed separately |

</details>

<details>
<summary><b>Working sets and audit</b></summary>

| Variable | CLI flag | Default | Description |
|---|---|---|---|
| `MCP_WS_PERSIST` | `--ws-persist` | `false` | Keep working sets in `<data-dir>/data/workingsets.db` across restarts |
| `MCP_WS_TTL_MINUTES` | `--ws-ttl-minutes` | `15` | Idle minutes before a working set expires |
| `MCP_WS_PERSIST_MAX_MB` | `--ws-persist-max-mb` | `64` | Largest working set persisted |
| `MCP_WS_SWEEP_SECONDS` | `--ws-sweep-seconds` | `60` | Cleanup interval (5..3600) |
| `AUDIT_ENABLED` | `--audit-enabled` | `false` | Audit every staged change and commit |

</details>

<details>
<summary><b>Limits and logging</b></summary>

| Variable | CLI flag | Default | Description |
|---|---|---|---|
| `MCP_MAX_PAGE_SIZE` | `--max-page-size` | `1000` | Largest page; larger requests are clamped with a warning |
| `MCP_MAX_ATTACHMENT_MB` | `--max-attachment-mb` | `25` | Largest attachment up/downloaded |
| `MCP_MAX_REPORT_MB` | `--max-report-mb` | `10` | Largest report returned |
| `MCP_MAX_CONCURRENT_TOOL_CALLS` | `--max-concurrent-tool-calls` | `0` | Parallel calls before `server_busy` (0 = unlimited) |
| `MCP_SERVER_LOG_SCAN_MB` | `--server-log-scan-mb` | `64` | Most of Maximo's log scanned per call |
| `MCP_LOG_MAX_MB` / `MCP_LOG_MAX_FILES` | `--log-max-mb` / `--log-max-files` | `20` / `30` | Log rotation |
| `MCP_SERVER_DEBUG` | `--debug` | `false` | Debug logs |

</details>

More options (logging, OAuth bootstrap, async commit, metadata API key):
[docs / configuration](https://soumyaprasadrana.github.io/maximo-mcp-server/guide/configuration).

---

## Troubleshooting

| You see | Do this |
|---|---|
| `metadata_sync_in_progress` on every call | The first full sync is running (`mcp_server_status` shows progress), or `MAXMCPMETADATA` is missing. Or start with `--reconcile-lazy`. |
| New tools are missing | Restart the MCP client (it caches the tool list); configuration tools need `--copilot-mode`. |
| `AUTH_REDIRECT` | On MAS, API keys work on `/api/...` paths; `/oslc/...` redirects to the login page. Keep the default paths and check the key. |
| `BMXAA...` in an error | That is Maximo's own reason, passed through unchanged -- fix the input it names. |
| `esig_required` | Pass `esigAuth` (base64 of the password only) and `esigReason`, or set `MAXIMO_ESIG_AUTH` on the server. |
| `invalid_target_status` / BLOCKED plan | Use one of the `valid_next_statuses` it returns. |
| `input_node_reached` | The workflow needs a choice only the Maximo UI can make: finish it in the Inbox. |
| HTTP 401 from the server | Get an OAuth token (see [HTTP and OAuth](#http-and-oauth)). |

More: [docs / troubleshooting and guides](https://soumyaprasadrana.github.io/maximo-mcp-server/guide/getting-started).

---

## Versions and license

| Published on npm | This package | Edition |
|---|---|---|
| **2.1.0** | **2.1.0** | one edition -- every tool is in this package |

**What is new in 2.1.0:** every request pinned to `MAXIMO_URL`; workflow routing and start;
valid-next-status checks; field lookups (incl. table domains); group-by aggregation; BIRT reports;
integration errors and opt-in Maximo server log; attachment upload; limits and clearer auth
errors. Details: [CHANGELOG](CHANGELOG.md#210----2026-11-07).

**License.** Every tool ships in this package; there are no paid tiers or hidden editions. The
source is not open: the software is proprietary and free for non-commercial use (personal,
educational, research) under the terms in [LICENSE](LICENSE). For commercial use or
redistribution, contact the author.

---

## Support

- Documentation: https://soumyaprasadrana.github.io/maximo-mcp-server
- Issues: https://github.com/soumyaprasadrana/maximo-mcp-server/issues
- Related: [maximo-kit](https://github.com/soumyaprasadrana/maximo-kit) -- a Spec Kit extension that
  drives this server through design-first Maximo configuration recipes
- Contact: **soumyaprasad.rana@gmail.com**
