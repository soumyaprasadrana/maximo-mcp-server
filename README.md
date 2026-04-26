# maximo-mcp-server

[![npm version](https://img.shields.io/npm/v/@soumyaprasadrana/maximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/%40soumyaprasadrana%2Fmaximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![Node.js](https://img.shields.io/badge/node-%3E%3D20-339933.svg)](https://nodejs.org)
[![Repository](https://img.shields.io/badge/repo-github-black.svg)](https://github.com/soumyaprasadrana/maximo-mcp-server)

Enterprise MCP server for IBM Maximo Application Suite.

This server provides a governed interaction layer between AI agents and Maximo by combining:

- metadata-aware discovery and query construction
- a stateful Working Set transaction model
- explicit stage/preview/commit lifecycle for data changes

## Architecture

```text
AI Agent (MCP Client)
        |
        | MCP (stdio/http)
        v
maximo-mcp-server
  |- Metadata Engine (SQLite-backed)
  |- OS Query Builder
  |- Working Set Engine (stateful session + staged changes)
        |
        v
IBM Maximo REST / OSLC APIs
```

## Prerequisites

- Node.js 20 or later
- npm 10 or later
- Network access to your Maximo environment
- Maximo automation script `MAXMCPMETADATA.py` configured in your Maximo environment (mandatory)

Verify:

```bash
node -v
npm -v
```

### Mandatory Maximo Setup

Before running the MCP server, configure the metadata extraction automation script in Maximo:

- Script file: `MAXMCPMETADATA.py`
- Source URL: `https://raw.githubusercontent.com/soumyaprasadrana/maximo-mcp-server/refs/heads/main/MAXMCPMETADATA.py`

This script is required for metadata reconciliation and Object Structure intelligence used by the Metadata Engine.

## Installation

Install globally:

```bash
npm install -g @soumyaprasadrana/maximo-mcp-server
```

Global install is preferred for CLI usage because:

- startup is faster than `npx` (no per-run package resolution/install delay)
- it avoids transient `npx` cache/native dependency issues
- npm `-g` installs CLI tools globally so they can be run directly as commands

## Usage

Run the server:

```bash
maximo-mcp-server
```

CLI helpers:

```bash
maximo-mcp-server --version
maximo-mcp-server --help
```

Default transport is `stdio`.

Run in HTTP mode:

```bash
MCP_TRANSPORT=http \
MCP_SERVER_PORT=8001 \
MAXIMO_URL="https://your-maximo-host/maximo" \
MAXIMO_API_KEY="your-api-key" \
maximo-mcp-server
```

HTTP endpoints:

- `POST /mcp`
- `GET /health`

## Claude Desktop (stdio)

Add this to `claude_desktop_config.json`:

- Windows path: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS path: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "maximo": {
      "command": "maximo-mcp-server",
      "env": {
        "MAXIMO_URL": "https://your-maximo-host/maximo",
        "MAXIMO_API_KEY": "your-api-key",
        "MCP_DATA_BASE_DIR": "C:\\maximo-mcp",
        "MCP_LOGS_DIR": "C:\\maximo-mcp\\logs"
      }
    }
  }
}
```

Recommended folder setup before first run:

```powershell
New-Item -ItemType Directory -Force -Path C:\maximo-mcp, C:\maximo-mcp\data, C:\maximo-mcp\logs
```

```bash
mkdir -p /opt/maximo-mcp/data /opt/maximo-mcp/logs
```

Use persistent folders for:

- `MCP_DATA_BASE_DIR` -> metadata DB at `data/meta.db`
- `MCP_LOGS_DIR` -> rolling MCP logs (`mcp.YYYY-MM-DD.N.log`)

## IBM watsonx Orchestrate

IBM watsonx Orchestrate connects to the MCP server over HTTP using OAuth2 client credentials. Bearer token authentication is **mandatory** on all `/mcp` routes when using HTTP transport — there is no unauthenticated HTTP mode.

### Step 1 — Create an OAuth client

Run this once against your data directory. The server exits after printing the credentials.

```bash
npx -y @soumyaprasadrana/maximo-mcp-server@latest \
  --data-dir /opt/maximo-mcp/data \
  --setup-oauth \
  --oauth-client-id orchestrate-client \
  --oauth-scopes "read write delete"
```

Output:

```
╔══════════════════════════════════════════════════════════╗
║  OAuth Client Created                                    ║
║                                                          ║
║  Client ID:     orchestrate-client                       ║
║  Client Secret: <generated-secret>                       ║
║  Scopes:        read write delete                        ║
║                                                          ║
║  SAVE THESE CREDENTIALS — secret shown only once         ║
╚══════════════════════════════════════════════════════════╝
```

> `--oauth-client-id` and `--oauth-client-secret` are optional — both are auto-generated if omitted.
> If no client exists when the server first starts in HTTP mode, one is auto-generated and printed at startup.

### Step 2 — Start the server in HTTP mode

```bash
npx -y @soumyaprasadrana/maximo-mcp-server@latest \
  --data-dir /opt/maximo-mcp/data \
  --logs-dir /opt/maximo-mcp/logs \
  --maximo-url https://your-maximo-host/maximo \
  --maximo-api-key your-api-key-here \
  --transport http \
  --port 8001 \
  --log-to-console \
  --strict-tool-schema
```

> `--strict-tool-schema` is strongly recommended for watsonx Orchestrate. It removes `anyOf:[type,null]` patterns that can confuse the orchestrator into misreading structured object fields as plain strings.

### Step 3 — Configure watsonx Orchestrate

In Orchestrate, add a remote MCP server with:

| Field         | Value                                 |
| ------------- | ------------------------------------- |
| MCP URL       | `http://<your-host>:8001/mcp`         |
| Token URL     | `http://<your-host>:8001/oauth/token` |
| Grant type    | `client_credentials`                  |
| Client ID     | _(from Step 1)_                       |
| Client Secret | _(from Step 1)_                       |
| Scope         | `read write delete`                   |

### OAuth token endpoint reference

```
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
client_id=orchestrate-client
client_secret=<your-secret>
scope=read write delete
```

```json
{
  "access_token": "<JWT>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read write delete"
}
```

Token TTL defaults to 3600 s and is configurable via `--oauth-token-ttl <seconds>` / `MCP_OAUTH_TOKEN_TTL`.

### Scopes

| Scope    | Covers                                                                                                                  |
| -------- | ----------------------------------------------------------------------------------------------------------------------- |
| `read`   | Query, load, and retrieve records (`os_query_builder`, `ws_load`, `ws_get_records`, `maximo_get_metadata`, attachments) |
| `write`  | Stage and commit mutations (`ws_update_field`, `ws_multi_update`, `ws_batch_update`, `ws_commit`, `ws_add_record`)      |
| `delete` | Destructive operations (`ws_delete_record`, `ws_remove`)                                                                |

> **Note:** Per-tool scope enforcement (blocking a `write`-only token from calling delete tools) is planned for a future release. The current release enforces that a valid token with any registered scope is required for all `/mcp` requests.

## Configuration

### Required

| Variable            | Description                                                                                                    |
| ------------------- | -------------------------------------------------------------------------------------------------------------- |
| `MAXIMO_URL`        | Base URL of Maximo instance                                                                                    |
| `MAXIMO_API_KEY`    | API key used by server calls                                                                                   |
| `MCP_DATA_BASE_DIR` | Mandatory persistent base directory for metadata DB (`data/meta.db`). Required for on-demand MCP startup flows |
| `MCP_LOGS_DIR`      | Mandatory persistent log directory. Required to monitor startup metadata sync progress                         |

### Common Optional

| Variable                       | Default     | Description                                                                                                                                                                                                                    |
| ------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `MCP_TRANSPORT`                | `stdio`     | `stdio` or `http`                                                                                                                                                                                                              |
| `MCP_SERVER_PORT`              | `8001`      | HTTP port when `MCP_TRANSPORT=http`                                                                                                                                                                                            |
| `MCP_LOG_ROTATE_DAILY`         | `true`      | Rotate logs by date                                                                                                                                                                                                            |
| `MCP_LOG_MAX_MB`               | `20`        | Max size per log file before rolling                                                                                                                                                                                           |
| `MCP_LOG_MAX_FILES`            | `30`        | Max rotated log files retained                                                                                                                                                                                                 |
| `MCP_RECONCILE_ON_STARTUP`     | `true`      | Reconcile metadata on startup                                                                                                                                                                                                  |
| `MCP_RECONCILE_ON_RESTART`     | `false`     | Force startup reconcile on every restart                                                                                                                                                                                       |
| `MCP_RECONCILE_WEEKLY_ENABLED` | `false`     | Weekly background reconcile                                                                                                                                                                                                    |
| `MCP_RECONCILE_WEEKLY_CRON`    | `0 3 * * 0` | Cron expression for weekly reconcile                                                                                                                                                                                           |
| `MCP_EMBEDDINGS_MODE`          | `none`      | `none`, `local`, or `openai`                                                                                                                                                                                                   |
| `MCP_LOG_TO_CONSOLE`           | `false`     | Print logs to console                                                                                                                                                                                                          |
| `MCP_SERVER_DEBUG`             | `false`     | Enable debug logs                                                                                                                                                                                                              |
| `MCP_STRICT_TOOL_SCHEMA`       | `false`     | Use strict (no-nullable) JSON Schemas for MCP tools. Removes `anyOf:[type,null]` patterns that can confuse LLM orchestrators. Recommended when connecting IBM watsonx Orchestrate. Equivalent CLI flag: `--strict-tool-schema` |
| `MCP_OAUTH_TOKEN_TTL`          | `3600`      | OAuth2 access token lifetime in seconds (HTTP transport only). Equivalent CLI flag: `--oauth-token-ttl`                                                                                                                        |
| `AUDIT_ENABLED`                | `false`     | Working Set audit logging                                                                                                                                                                                                      |
| `AUDIT_DB_DIR`                 | `./audit`   | Directory for monthly audit sqlite files                                                                                                                                                                                       |
| `AUDIT_RETENTION_MONTHS`       | `12`        | Retention for audit DBs                                                                                                                                                                                                        |
| `AUDIT_FLUSH_INTERVAL_MS`      | `500`       | Buffered audit flush interval                                                                                                                                                                                                  |
| `AUDIT_BATCH_SIZE`             | `100`       | Max events per audit flush                                                                                                                                                                                                     |

Suggested runtime visibility:

- `MCP_DATA_BASE_DIR` and `MCP_LOGS_DIR` are mandatory for reliable startup and observability.
- During startup reconcile, tool calls return `metadata_sync_in_progress` until sync completes.

### Initial Metadata Sync Timing

- First-time metadata load can take up to 5 minutes depending on Maximo metadata size.
- Example observed run: `initialReconcile took 315.713 seconds` on `2026-04-04`.
- Check files in `MCP_LOGS_DIR` to track progress when an MCP client initializes the server on demand.

Example log sequence:

```text
2026-04-04T05:32:56.299Z [loadMboMetadata] INFO loadMboMetadata start
2026-04-04T05:32:58.635Z [loadMboMetadata] INFO loadMboMetadata finished
2026-04-04T05:32:58.639Z [MetadataEngine-38992] WARN refreshEmbeddings skipped - embedder not initialized
2026-04-04T05:32:58.641Z [MetadataEngine-38992] INFO initialReconcile took 315.713 seconds
2026-04-04T05:32:58.642Z [MetadataEngine-38992] INFO initialReconcile finished - timestamp saved
```

## Tool Reference

## Metadata and Discovery

### `maximo_get_metadata`

Purpose:

- Resolves `maximo://` URIs for Object Structure discovery and schema lookup.
- This is the grounding tool before query building.

High-value URI patterns:

- `maximo://os/search/{query}`
  - Finds relevant Object Structures by intent keywords.
- `maximo://os/{osName}/schema`
  - Returns API-scoped schema for parent object fields.
- `maximo://os/{osName}/relatedObjects`
  - Returns child relationships and object names.
  - Use `relationshipName` in `childOptions`.
- `maximo://os/{osName}/subschemas/{childObject}`
  - Returns child schema to safely filter child rows.

Behavior:

- Gives OS-scoped metadata (preferred for secure, API-enabled field use).
- Avoids guesswork on field names, relationship names, and object coverage.

### `os_query_builder`

Purpose:

- Builds validated OSLC query URLs.
- Creates and returns a Working Set session (`wsId`) as part of query setup.

Capabilities:

- Structured `where` conditions (`=`, `!=`, `in`, `like`, `isnull`, `isnotnull`)
- Parent filtering and child traversal patterns
- `select`, `orderBy`, `pageSize`, `childOptions`
- saved query support (`savedQuery`, `savedQueryParams`)

Behavior:

- This is the official Working Set creation path.
- `ws_create` is deprecated/removed for agent usage.

## Working Set Tools

Working Set is a stateful in-memory session tied to query context.

### Read and Load

| Tool             | What it does                                   | Notes                                    |
| ---------------- | ---------------------------------------------- | ---------------------------------------- |
| `ws_load`        | Loads records from Maximo into the working set | Supports `useLean=true` compression mode |
| `ws_get_records` | Returns loaded records from working set memory | Supports `useLean=true`                  |
| `ws_get_active`  | Returns current active record                  | For guided record-level updates          |

### Update and Stage Changes

| Tool                 | What it does                                 | Notes                                  |
| -------------------- | -------------------------------------------- | -------------------------------------- |
| `ws_update_field`    | Stages one field update on one record        | No immediate Maximo mutation           |
| `ws_multi_update`    | Stages multiple field updates across records | Batch style for known targets          |
| `ws_batch_update`    | Stages updates based on filter/diff spec     | Useful for many-record transformations |
| `ws_set_active`      | Sets active record by restID                 | Simplifies sequential updates          |
| `ws_init_new_record` | Creates schema-based draft for new resource  | Returns metadata + draft skeleton      |
| `ws_add_record`      | Stages a new record insertion                | Commit required to persist             |
| `ws_delete_record`   | Stages a delete operation                    | Commit required to persist             |

### Review and Finalize

| Tool                 | What it does                                   | Notes                       |
| -------------------- | ---------------------------------------------- | --------------------------- |
| `ws_preview_changes` | Returns staged diff (create/update/delete)     | Review point before commit  |
| `ws_commit`          | Validates and applies staged changes to Maximo | Explicit write boundary     |
| `ws_discard`         | Drops all staged changes                       | Keeps original loaded state |
| `ws_remove`          | Removes working set from memory                | Session cleanup             |

### Attachments

| Tool                  | What it does                                       |
| --------------------- | -------------------------------------------------- |
| `ws_list_attachments` | Lists record doclinks in working set context       |
| `ws_get_attachment`   | Retrieves attachment content by identifier or href |

### Audit

| Tool                    | What it does                                                 |
| ----------------------- | ------------------------------------------------------------ |
| `maximo_get_audit_logs` | Fetches Working Set audit events (when `AUDIT_ENABLED=true`) |

## Orchestration Patterns

### Pattern A: Read-Only Work Order Planning Agent

Goal:

- Pull open/high-priority work orders
- Identify stale items and workload clusters
- Suggest plan without mutating Maximo

Step chain:

1. Discover best OS for work orders:
   - `maximo_get_metadata` with `maximo://os/search/work+order`
2. Inspect schema and relationships:
   - `maximo_get_metadata` with `maximo://os/{osName}/schema`
   - `maximo_get_metadata` with `maximo://os/{osName}/relatedObjects`
3. Build query + working set:
   - `os_query_builder` with status/owner/site filters
4. Load and retrieve records:
   - `ws_load`
   - `ws_get_records`
5. Optional enrichment:
   - `ws_list_attachments` for selected records
6. Produce time-aware plan:
   - prioritize by status, priority, age, and recency signals
   - no calls to `ws_commit`

Example query payload:

```json
{
  "osName": "MXAPIWO",
  "opAction": "query",
  "pageSize": 50,
  "select": {
    "fields": [
      "wonum",
      "description",
      "status",
      "wopriority",
      "siteid",
      "owner",
      "reportdate"
    ]
  },
  "where": {
    "conditions": [
      { "field": "status", "op": "in", "value": ["WAPPR", "APPR", "INPRG"] },
      { "field": "owner", "op": "=", "value": "{{user_id}}" }
    ]
  },
  "orderBy": { "rules": ["wopriority desc", "reportdate asc"] }
}
```

### Pattern B: Controlled Update Workflow

Goal:

- Apply governed status/field changes with explicit review gate.

Step chain:

1. `os_query_builder` -> create `wsId`
2. `ws_load` -> pull records
3. `ws_update_field` / `ws_multi_update` / `ws_batch_update` -> stage changes
4. `ws_preview_changes` -> inspect exact diff
5. `ws_commit` -> persist
6. `ws_remove` -> cleanup

## Operational Notes

- First reconcile can be slower on large Maximo metadata sets.
- For deterministic startup in constrained environments, keep `MCP_EMBEDDINGS_MODE=none`.
- LEAN mode (`useLean=true`) helps reduce token cost for large result sets.

## Support

GitHub issues: https://github.com/soumyaprasadrana/maximo-mcp-server/issues
