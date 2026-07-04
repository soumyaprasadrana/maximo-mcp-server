# maximo-mcp-server

[![npm version](https://img.shields.io/npm/v/@soumyaprasadrana/maximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/%40soumyaprasadrana%2Fmaximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![Node.js](https://img.shields.io/badge/node-%3E%3D20-339933.svg)](https://nodejs.org)
[![Repository](https://img.shields.io/badge/repo-github-black.svg)](https://github.com/soumyaprasadrana/maximo-mcp-server)

Enterprise MCP server for IBM Maximo Application Suite.

Provides a governed interaction layer between AI agents and Maximo combining:

- Metadata-aware discovery and query construction
- Stateful Working Set transaction model with staged preview/commit lifecycle
- Business process tools: status transitions, workflow approvals
- Built-in OAuth 2.0 authorization server (HTTP transport)
- IBM watsonx Orchestrate compatible strict tool schemas
- Resumable metadata sync with per-stage checkpoints
- Optional dev-mode diagnostic tools accessible from within the agent

## Architecture

```text
AI Agent (MCP Client)
        |
        | MCP (stdio / http + OAuth 2.0)
        v
maximo-mcp-server
  |- Metadata Engine  (SQLite, resumable sync, vector search)
  |- OS Query Builder (metadata-validated OSLC queries)
  |- Working Set Engine (stateful session, staged changes, audit)
  |- Business Process Tools (status change, workflow)
  |- OAuth 2.0 Server (client_credentials grant, JWT, HTTP transport)
  |- Dev Diagnostic Tools   (log streaming, server status — dev mode)
        |
        v
IBM Maximo REST / OSLC APIs
```

---

## What's New in v1.1.8

### Built-in OAuth 2.0 Authorization Server (HTTP transport)

When running with `--transport http`, the server now exposes a standards-compliant OAuth 2.0 authorization endpoint at `POST /oauth/token`. All registered MCP clients must obtain a Bearer token before connecting.

- **Grant type:** `client_credentials`
- **Token format:** signed JWT (HS256), secret auto-generated and persisted in SQLite
- **Client registry:** stored in the metadata SQLite DB (secrets are hashed — never recoverable after creation)
- **One-shot setup:** `maximo-mcp-server --setup-oauth --data-dir /opt/maximo-mcp`
- **Credentials file:** written to `MCP_OAUTH_CREDS_DIR` at client creation time (plain-text secret is only shown once)

See the [OAuth Setup](#oauth-20-setup-http-transport-only) section below.

### IBM watsonx Orchestrate Compatibility

Set `MCP_STRICT_TOOL_SCHEMA=true` to switch all tool input schemas to strict variants with no nullable/union types. IBM watsonx Orchestrate requires JSON Schemas without `anyOf`/`oneOf` constructs; this mode produces a fully flat, string-only schema that passes Orchestrate's tool import validation.

### Non-Blocking Preview Validation

`ws_preview_changes` now runs a full validation pass (domain values, readonly fields, type checks) and returns results as `validation_warnings` alongside the diff. These are advisory only — `ws_commit` no longer blocks on validation. Show warnings to the user and let them decide whether to adjust or proceed. Maximo itself remains the final authority on data validity.

### Create Record Workflow

The two-tool create flow is now fully supported: `ws_init_new_record` fetches a schema-driven template from Maximo and returns a draft skeleton; `ws_update_draft` merges user-supplied fields into the draft. Follow with `ws_preview_changes` → `ws_commit`.

### Context Session Store

Six new `ctx_*` tools provide lightweight key-value session memory scoped to an agent conversation. Useful for storing intermediate results, user preferences, or cross-tool state without round-tripping to Maximo.

---

## Prerequisites

- Node.js 20 or later
- npm 10 or later
- Network access to your Maximo instance
- Maximo automation script `MAXMCPMETADATA` deployed (mandatory — see below)

```bash
node -v   # must be >= 20
npm -v
```

### Mandatory: Deploy MAXMCPMETADATA Automation Script

The metadata engine requires this script to extract object and attribute metadata from Maximo.

- Script name: `MAXMCPMETADATA`
- Source: `https://raw.githubusercontent.com/soumyaprasadrana/maximo-mcp-server/refs/heads/main/MAXMCPMETADATA.py`

Deploy steps (Maximo Administration):

1. Go to **System Configuration → Platform Configuration → Automation Scripts**
2. Create a new script named `MAXMCPMETADATA`
3. Paste the content from the URL above
4. Activate the script

Without this script the server starts but metadata sync fails and all tools return `metadata_sync_in_progress`.

---

## Installation

Install globally (recommended for CLI use):

```bash
npm install -g @soumyaprasadrana/maximo-mcp-server
```

Verify:

```bash
maximo-mcp-server --version
maximo-mcp-server --help
```

---

## Starting the Server

### Option 1 — Environment variables

```bash
export MAXIMO_URL="https://your-maximo-host/maximo"
export MAXIMO_API_KEY="your-api-key"
export MCP_DATA_BASE_DIR="/opt/maximo-mcp"
export MCP_LOGS_DIR="/opt/maximo-mcp/logs"

maximo-mcp-server
```

Windows PowerShell:

```powershell
$env:MAXIMO_URL        = "https://your-maximo-host/maximo"
$env:MAXIMO_API_KEY    = "your-api-key"
$env:MCP_DATA_BASE_DIR = "C:\maximo-mcp"
$env:MCP_LOGS_DIR      = "C:\maximo-mcp\logs"

maximo-mcp-server
```

### Option 2 — CLI flags

```bash
maximo-mcp-server \
  --maximo-url     "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key" \
  --data-dir       /opt/maximo-mcp \
  --logs-dir       /opt/maximo-mcp/logs
```

HTTP transport with dev mode:

```bash
maximo-mcp-server \
  --maximo-url     "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key" \
  --transport      http \
  --port           8001 \
  --data-dir       /opt/maximo-mcp \
  --logs-dir       /opt/maximo-mcp/logs \
  --dev-mode
```

Force a full metadata re-sync:

```bash
maximo-mcp-server \
  --maximo-url     "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key" \
  --data-dir       /opt/maximo-mcp \
  --force-reconcile
```

### Option 3 — .env file

```dotenv
MAXIMO_URL=https://your-maximo-host/maximo
MAXIMO_API_KEY=your-api-key
MCP_DATA_BASE_DIR=/opt/maximo-mcp
MCP_LOGS_DIR=/opt/maximo-mcp/logs
MCP_TRANSPORT=stdio
```

Then start with no extra arguments:

```bash
maximo-mcp-server
```

---

## Persistent Storage Setup (required)

**Linux / macOS:**

```bash
mkdir -p /opt/maximo-mcp/data /opt/maximo-mcp/logs
```

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path C:\maximo-mcp, C:\maximo-mcp\data, C:\maximo-mcp\logs
```

| Directory                 | Env var             | Contents                                   |
| ------------------------- | ------------------- | ------------------------------------------ |
| `<data-dir>/data/meta.db` | `MCP_DATA_BASE_DIR` | SQLite metadata + OAuth client database    |
| `<logs-dir>/`             | `MCP_LOGS_DIR`      | Rolling log files (`mcp.YYYY-MM-DD.N.log`) |

---

## Claude Desktop (stdio)

Add to `claude_desktop_config.json`:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

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

Restart Claude Desktop after saving.

---

## IBM watsonx Orchestrate

Set `MCP_STRICT_TOOL_SCHEMA=true` when registering the server with IBM watsonx Orchestrate. This activates strict (no-nullable, no-union) JSON Schemas for all tool inputs — required for Orchestrate's tool import validation.

```json
{
  "mcpServers": {
    "maximo": {
      "command": "maximo-mcp-server",
      "env": {
        "MAXIMO_URL": "https://your-maximo-host/maximo",
        "MAXIMO_API_KEY": "your-api-key",
        "MCP_DATA_BASE_DIR": "C:\\maximo-mcp",
        "MCP_LOGS_DIR": "C:\\maximo-mcp\\logs",
        "MCP_STRICT_TOOL_SCHEMA": "true"
      }
    }
  }
}
```

For HTTP transport with Orchestrate, also configure OAuth (see below).

---

## OAuth 2.0 Setup (HTTP transport only)

When `MCP_TRANSPORT=http`, the server enforces OAuth 2.0 Bearer token authentication on all MCP connections. Clients use the `client_credentials` grant to obtain a JWT and send it as `Authorization: Bearer <token>`.

### Step 1 — Create an OAuth client

```bash
maximo-mcp-server \
  --setup-oauth \
  --data-dir /opt/maximo-mcp \
  --maximo-url "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key"
```

The command prints the `client_id` and `client_secret` to stdout. **Save the secret — it is shown only once.** If `MCP_OAUTH_CREDS_DIR` is set, the credentials are also written to `oauth-credentials.json` in that directory.

### Step 2 — Obtain a token at runtime

```bash
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=<your-client-id>" \
  -d "client_secret=<your-client-secret>"
```

Response:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Step 3 — Connect the MCP client

Send the token as `Authorization: Bearer <access_token>` on every MCP HTTP request.

### Managing clients

```bash
# List registered clients (secrets not shown)
maximo-mcp-server --list-oauth-clients --data-dir /opt/maximo-mcp \
  --maximo-url "..." --maximo-api-key "..."

# Remove a client
maximo-mcp-server --delete-oauth-client <client-id> --data-dir /opt/maximo-mcp \
  --maximo-url "..." --maximo-api-key "..."
```

### OAuth environment variables

| Variable                  | Default | Description                                     |
| ------------------------- | ------- | ----------------------------------------------- |
| `MCP_OAUTH_TOKEN_TTL`     | `3600`  | JWT expiry in seconds                           |
| `MCP_OAUTH_CREDS_DIR`     | —       | Directory where credentials file is written     |
| `MCP_SETUP_OAUTH`         | —       | Set to `1` to run setup-oauth mode and exit     |
| `MCP_LIST_OAUTH_CLIENTS`  | —       | Set to `1` to list clients and exit             |
| `MCP_DELETE_OAUTH_CLIENT` | —       | Set to `<clientId>` to delete a client and exit |

---

## Metadata Sync

On first startup the server downloads all Maximo Object Structure metadata. This can take several minutes on large Maximo environments.

**Sync is resumable** — if the server is restarted mid-sync, the next startup resumes from the last completed stage.

Sync stages:

| Stage | Name                  | What it fetches                                                |
| ----- | --------------------- | -------------------------------------------------------------- |
| 1     | Fetching API metadata | List of all Object Structures from `/api/apimeta`              |
| 2     | Loading schemas       | JSON schema for each OS (one request per OS)                   |
| 3     | Loading MBO metadata  | Object/attribute/relationship data via `MAXMCPMETADATA` script |

While sync is running, tool calls return a `metadata_sync_in_progress` response with current stage and percentage. Enable `--dev-mode` and use `mcp_server_status` / `mcp_read_logs` to monitor from within the agent.

### Sync startup modes

| Mode                          | Flag               | Behaviour                                                                                           |
| ----------------------------- | ------------------ | --------------------------------------------------------------------------------------------------- |
| **Fire-and-forget** (default) | _(none)_           | Server starts immediately. Sync runs in-process in the background.                                  |
| **Synchronous**               | `--reconcile-sync` | Server blocks until sync completes before accepting connections.                                    |
| **Background worker**         | `--bg-sync-worker` | Sync is spawned as a fully detached child process. File lock prevents duplicate workers on restart. |

**Background worker example (Claude Desktop):**

```json
{
  "mcpServers": {
    "maximo": {
      "command": "maximo-mcp-server",
      "env": {
        "MAXIMO_URL": "https://your-maximo-host/maximo",
        "MAXIMO_API_KEY": "your-api-key",
        "MCP_DATA_BASE_DIR": "C:\\maximo-mcp",
        "MCP_LOGS_DIR": "C:\\maximo-mcp\\logs",
        "MCP_BG_SYNC_WORKER": "true"
      }
    }
  }
}
```

---

## Configuration Reference

### Required

| Variable            | CLI flag           | Description                                |
| ------------------- | ------------------ | ------------------------------------------ |
| `MAXIMO_URL`        | `--maximo-url`     | Base URL of Maximo instance                |
| `MAXIMO_API_KEY`    | `--maximo-api-key` | API key for all Maximo calls               |
| `MCP_DATA_BASE_DIR` | `--data-dir`       | Persistent base dir (holds `data/meta.db`) |
| `MCP_LOGS_DIR`      | `--logs-dir`       | Persistent log directory                   |

### Transport

| Variable                 | CLI flag      | Default | Description                                          |
| ------------------------ | ------------- | ------- | ---------------------------------------------------- |
| `MCP_TRANSPORT`          | `--transport` | `stdio` | `stdio` or `http`                                    |
| `MCP_SERVER_PORT`        | `--port`      | `8001`  | HTTP port when transport=http                        |
| `MCP_STRICT_TOOL_SCHEMA` | —             | `false` | Strict (no-nullable) schemas for watsonx Orchestrate |

### Logging

| Variable               | CLI flag             | Default | Description             |
| ---------------------- | -------------------- | ------- | ----------------------- |
| `MCP_LOG_ROTATE_DAILY` | `--log-rotate-daily` | `true`  | Rotate logs by date     |
| `MCP_LOG_MAX_MB`       | `--log-max-mb`       | `20`    | Max MB per log file     |
| `MCP_LOG_MAX_FILES`    | `--log-max-files`    | `30`    | Retained log files      |
| `MCP_LOG_TO_CONSOLE`   | `--log-to-console`   | `false` | Echo logs to console    |
| `MCP_SERVER_DEBUG`     | `--debug`            | `false` | Enable debug-level logs |

### Metadata Sync

| Variable                       | CLI flag                  | Default     | Description                                 |
| ------------------------------ | ------------------------- | ----------- | ------------------------------------------- |
| `MCP_RECONCILE_ON_STARTUP`     | `--reconcile-on-startup`  | `true`      | Sync on startup                             |
| `MCP_RECONCILE_ON_RESTART`     | `--force-reconcile`       | `false`     | Force full re-sync every restart            |
| `MCP_RECONCILE_WEEKLY_ENABLED` | `--reconcile-weekly`      | `false`     | Weekly background re-sync                   |
| `MCP_RECONCILE_WEEKLY_CRON`    | `--reconcile-weekly-cron` | `0 3 * * 0` | Cron expression for weekly sync             |
| `MCP_RECONCILE_SYNC`           | `--reconcile-sync`        | `false`     | Block server startup until sync completes   |
| `MCP_BG_SYNC_WORKER`           | `--bg-sync-worker`        | `false`     | Spawn sync as a detached background process |

### Embeddings

| Variable              | CLI flag            | Default | Description                  |
| --------------------- | ------------------- | ------- | ---------------------------- |
| `MCP_EMBEDDINGS_MODE` | `--embeddings-mode` | `none`  | `none`, `local`, or `openai` |

### Audit

| Variable                 | CLI flag            | Default   | Description                |
| ------------------------ | ------------------- | --------- | -------------------------- |
| `AUDIT_ENABLED`          | `--audit-enabled`   | `false`   | Working Set audit logging  |
| `AUDIT_DB_DIR`           | `--audit-dir`       | `./audit` | Monthly audit SQLite files |
| `AUDIT_RETENTION_MONTHS` | `--audit-retention` | `12`      | Audit retention in months  |

### Dev Mode

| Variable              | CLI flag     | Default | Description             |
| --------------------- | ------------ | ------- | ----------------------- |
| `MCP_ENABLE_DEV_MODE` | `--dev-mode` | `false` | Enable diagnostic tools |

When `MCP_ENABLE_DEV_MODE=true` two additional MCP tools are registered:

- `mcp_server_status` — full diagnostic snapshot (sync stage/progress, DB counts, checkpoint state, log file list)
- `mcp_read_logs` — tail recent log entries with optional level filter

These tools bypass the metadata sync guard, so they work even during an active sync.

You meant raw Markdown **without wrapping the whole thing in another code fence**. Paste this directly into your README:

### Maximo Developer Copilot Mode

| Variable           | CLI flag         | Default | Description                                                |
| ------------------ | ---------------- | ------- | ---------------------------------------------------------- |
| `MCP_COPILOT_MODE` | `--copilot-mode` | `false` | Enables experimental Maximo Developer Copilot capabilities |

When `MCP_COPILOT_MODE=true`, the server enables experimental Maximo Developer Copilot capabilities using Migration Manager Object Structures.

This mode is intended for coding agents such as Claude and Cursor to develop, configure, and validate Maximo as a platform. It uses the server’s existing metadata discovery, Working Set staging, preview, explicit user approval, and commit lifecycle.

Migration Manager Object Structures must be enabled for OSLC discovery. Ensure the Maximo system property `mxe.oslc.validusewith` includes `MIGRATIONMGR`.

```text
INTEGRATION,OSLC,REPORTING,MIGRATIONMGR
```

Copilot metadata discovery uses all `useWith` values configured in `mxe.oslc.validusewith`. The server identifies Maximo Developer Copilot readiness when `MIGRATIONMGR` is configured and Migration Manager Object Structures are returned during metadata sync.

> **Experimental feature:** Use only in development environments. Review every Working Set preview and validation warning before committing configuration changes.

---

## Tool Reference

### Metadata and Discovery

#### `maximo_get_metadata`

Resolves `maximo://` URIs for Object Structure discovery and schema lookup.

| URI pattern                                     | Returns                                    |
| ----------------------------------------------- | ------------------------------------------ |
| `maximo://os/search/{query}`                    | Object Structures matching keyword         |
| `maximo://os/{osName}/schema`                   | API-scoped schema for parent object fields |
| `maximo://os/{osName}/relatedObjects`           | Child relationships and object names       |
| `maximo://os/{osName}/subschemas/{childObject}` | Child object schema                        |

Always start here before building queries.

#### `os_query_builder`

Builds validated OSLC query URLs and creates the Working Set session (`wsId`). This is the official Working Set creation path.

Supports: `where` conditions, `select`, `orderBy`, `pageSize`, `childOptions`, `savedQuery`.

---

### Working Set Tools

Working Set is a stateful in-memory session tied to query context. All mutations are staged and must be explicitly committed.

#### Read and Load

| Tool             | What it does                                   |
| ---------------- | ---------------------------------------------- |
| `ws_load`        | Loads records from Maximo into the working set |
| `ws_get_records` | Returns loaded records from working set memory |
| `ws_get_active`  | Returns the current active record              |

Both `ws_load` and `ws_get_records` support `useLean=true` for 40–60% token reduction on large result sets.

#### Stage Changes

| Tool                 | What it does                                                           |
| -------------------- | ---------------------------------------------------------------------- |
| `ws_update_field`    | Stages one field update on one record                                  |
| `ws_multi_update`    | Stages multiple field updates across records                           |
| `ws_batch_update`    | Stages updates based on filter/diff spec                               |
| `ws_set_active`      | Sets active record — accepts index, \_tempId, restId, or href          |
| `ws_init_new_record` | Creates a schema-based draft for a new record (create flow)            |
| `ws_update_draft`    | Merges user-supplied fields into a draft created by ws_init_new_record |
| `ws_delete_record`   | Stages a delete operation                                              |

#### Review and Finalize

| Tool                 | What it does                                                                           |
| -------------------- | -------------------------------------------------------------------------------------- |
| `ws_preview_changes` | Returns staged diff + non-blocking `validation_warnings` for user review before commit |
| `ws_commit`          | Plans and applies staged changes to Maximo (validation warnings do not block commit)   |
| `ws_discard`         | Drops staged changes, keeps loaded state                                               |
| `ws_remove`          | Removes working set from memory (session cleanup)                                      |

**Validation warning behavior:** `ws_preview_changes` runs a full validation pass (domain values, readonly flags, type checks) and returns results in `validation_warnings`. Present these to the user and let them decide whether to adjust or proceed. `ws_commit` does not re-run validation — it goes directly to plan and execute, allowing Maximo to be the final authority.

#### Attachments

| Tool                  | What it does                               |
| --------------------- | ------------------------------------------ |
| `ws_list_attachments` | Lists record doclinks                      |
| `ws_get_attachment`   | Retrieves attachment content by ID or href |

#### Audit

| Tool                    | What it does                                                     |
| ----------------------- | ---------------------------------------------------------------- |
| `maximo_get_audit_logs` | Fetches Working Set audit events (requires `AUDIT_ENABLED=true`) |

---

### Business Process Tools

#### Status Change

Status changes are executed via Maximo's `changeStatus` action — not as field updates. Use the two-tool pattern to enforce user review before execution.

##### `maximo_plan_status_change`

Validates a proposed status transition and returns a preview without making any changes.

- Fetches current record status
- Checks `allowedactions` to verify `changeStatus` is permitted
- Returns: current status, target status, transition verdict, full allowed actions list

**Always call this first. Show the result to the user before proceeding.**

##### `maximo_change_status`

Executes the status transition after user confirmation.

- Calls `getAllowedActions` immediately before execution (guards against race conditions)
- Rejects if `changeStatus` is not in the allowed actions

Example flow:

```
1. os_query_builder → find the work order, get wsId + restId
2. maximo_plan_status_change osName=MXAPIWO restId=12345 newStatus=CLOSE memo="Job complete"
3. → Show plan to user, get confirmation
4. maximo_change_status osName=MXAPIWO restId=12345 newStatus=CLOSE memo="Job complete"
```

#### Workflow

##### `maximo_get_workflow_assignments`

Queries the `MXAPIWFASSIGNMENT` object structure to list pending workflow tasks.

Filters: `personId`, `roleId`, `processName`, `ownerTable`, `pageSize`.

Use `includeAllowedActions=true` to fetch the allowed actions on each owning record in one call.

##### `maximo_send_workflow_response`

Invokes a workflow action on the owning record (work order, service request, etc.).

- Call `getAllowedActions` before execution — rejects if action is not available
- Omit `actionName` to get a discovery response (allowed actions only)

Common action names (vary by workflow configuration):

| Action     | Typical meaning         |
| ---------- | ----------------------- |
| `wfappr`   | Approve                 |
| `wfcanreq` | Cancel request / reject |
| `wfreject` | Reject                  |
| `wfaccept` | Accept task             |
| `wfreturn` | Return for rework       |

Example flow:

```
1. maximo_get_workflow_assignments personId=JSMITH includeAllowedActions=true
2. → Returns ownerid=5678, ownertable=WORKORDER, _allowedActions=[wfappr, wfcanreq]
3. maximo_send_workflow_response osName=MXAPIWO restId=5678 actionName=wfappr params={memo:"Approved"}
```

---

### Context Session Store

Six lightweight key-value tools for storing agent state across tool calls within a conversation.

| Tool         | What it does                                        |
| ------------ | --------------------------------------------------- |
| `ctx_create` | Creates a new named session store                   |
| `ctx_get`    | Reads a value by key from a session                 |
| `ctx_set`    | Writes or overwrites a value by key                 |
| `ctx_remove` | Removes a single key from a session                 |
| `ctx_delete` | Deletes an entire session                           |
| `ctx_list`   | Lists all keys (and optionally values) in a session |

Useful for caching intermediate query results, tracking multi-step workflow state, or storing user preferences without round-tripping to Maximo.

---

### Dev Diagnostic Tools _(requires `MCP_ENABLE_DEV_MODE=true`)_

#### `mcp_server_status`

Returns a full diagnostic snapshot: server version, transport, PID, uptime, live sync progress, checkpoint state, DB record counts, active config, log file list.

#### `mcp_read_logs`

Tails log entries from MCP server log files.

| Parameter | Default  | Description                                         |
| --------- | -------- | --------------------------------------------------- |
| `lines`   | 100      | Number of recent lines to return (0 = all)          |
| `level`   | `all`    | Filter: `all`, `info`, `warn`, `error`, `debug`     |
| `file`    | (latest) | Specific log filename (e.g. `mcp.2026-04-11.1.log`) |

---

## Orchestration Patterns

### Pattern A — Read-Only Analysis

```
1. maximo_get_metadata  maximo://os/search/work+order
2. maximo_get_metadata  maximo://os/{osName}/schema
3. os_query_builder     with status/priority/site filters
4. ws_load              useLean=true
5. ws_get_records       analyze and report
6. ws_remove            cleanup
```

### Pattern B — Governed Field Update

```
1. os_query_builder
2. ws_load
3. ws_update_field / ws_multi_update / ws_batch_update
4. ws_preview_changes   → show diff + any validation_warnings to user
5. ws_commit            → persist (after user confirms)
6. ws_remove
```

### Pattern C — Create New Record

```
1. ws_init_new_record   osName=MXAPISR
   → returns wsId, draftRecord skeleton, metadata
2. ws_update_draft      wsId, fields={description:"...", reportedby:"...", ...}
3. ws_preview_changes   → review draft + validation_warnings
4. ws_commit            → creates the record in Maximo
5. ws_remove
```

### Pattern D — Status Transition

```
1. os_query_builder     → find record, get restId
2. maximo_plan_status_change  osName, restId, newStatus
3. → Show plan to user, wait for confirmation
4. maximo_change_status       osName, restId, newStatus, memo
```

### Pattern E — Workflow Approval

```
1. maximo_get_workflow_assignments  personId={me} includeAllowedActions=true
2. → Identify assignment, note ownerid + ownertable + _allowedActions
3. → Present to user: "Work order WO-1234 is waiting for your approval"
4. maximo_send_workflow_response    osName, restId=ownerid, actionName=wfappr
```

### Pattern F — Diagnostic (sync stalled)

```
1. mcp_server_status
   → Read sync.currentStageName, sync.progress.percentComplete
   → Read sync.checkpoint (last persisted stage)
   → Read sync.lastError
2. mcp_read_logs  level=error  lines=50
   → Look for network errors, script failures, or auth issues
```

---

## Operational Notes

- First metadata sync takes 3–6 minutes on large Maximo environments. Subsequent startups skip it (completed flag is persisted).
- Sync is resumable: if the server stops mid-sync, the next startup resumes from the last completed stage.
- Always set `MCP_DATA_BASE_DIR` and `MCP_LOGS_DIR` to persistent paths outside the Node.js working directory in orchestrated environments.
- `MCP_EMBEDDINGS_MODE=none` (default) is recommended for production. Local embeddings require native dependencies that may not build on all platforms.
- LEAN mode (`useLean=true` on `ws_load` / `ws_get_records`) reduces token usage by 40–60% on large result sets.
- OAuth client secrets are hashed in the SQLite DB and cannot be recovered. If a secret is lost, delete the client and create a new one.

---

## Support

GitHub issues: https://github.com/soumyaprasadrana/maximo-mcp-server/issues
