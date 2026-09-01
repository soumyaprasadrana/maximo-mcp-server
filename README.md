# maximo-mcp-server

[![npm version](https://img.shields.io/npm/v/@soumyaprasadrana/maximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/%40soumyaprasadrana%2Fmaximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![Node.js](https://img.shields.io/badge/node-%3E%3D20-339933.svg)](https://nodejs.org)
[![Repository](https://img.shields.io/badge/repo-github-black.svg)](https://github.com/soumyaprasadrana/maximo-mcp-server)

An MCP (Model Context Protocol) server for IBM Maximo Application Suite. It gives AI agents a
governed way to discover Maximo metadata, build validated OSLC queries, and stage, preview, and
commit business-data changes -- without hand-written REST calls.

## Key capabilities

- Metadata-aware discovery and OSLC query construction, validated against live Maximo schema
- A stateful Working Set model: load records, stage changes, preview a diff, then commit
- Business process tools for status transitions and workflow approvals
- Built-in OAuth 2.0 authorization server for HTTP transport
- Strict tool schemas compatible with IBM watsonx Orchestrate
- Resumable metadata sync with per-stage checkpoints, safe to interrupt and restart
- Optional read-only mode and diagnostic tools for operational visibility

This package is the public edition, covering the full data-access surface described below. A
premium edition adds a set of Maximo configuration-management tools on top of the same base;
see [Premium edition](#premium-edition).

## Architecture

```text
AI Agent (MCP Client)
        |
        | MCP (stdio / http + OAuth 2.0)
        v
maximo-mcp-server
  |- Metadata Engine       (SQLite, resumable sync, optional vector search)
  |- OS Query Builder      (metadata-validated OSLC queries)
  |- Working Set Engine    (stateful session, staged changes, audit)
  |- Business Process Tools (status change, workflow)
  |- OAuth 2.0 Server      (client_credentials grant, JWT, HTTP transport)
  |- Diagnostic Tools      (log streaming, server status)
        |
        v
IBM Maximo REST / OSLC APIs
```

---

## Prerequisites

- Node.js 20 or later
- npm 10 or later
- Network access to your Maximo instance
- The `MAXMCPMETADATA` automation script deployed in Maximo (mandatory, see below)

```bash
node -v   # must be >= 20
npm -v
```

### Deploy the MAXMCPMETADATA automation script (mandatory)

The metadata engine requires this script to extract object and attribute metadata from Maximo.
Without it the server starts, but metadata sync fails and every tool call returns
`metadata_sync_in_progress`.

- Script name: `MAXMCPMETADATA`
- Source: `https://raw.githubusercontent.com/soumyaprasadrana/maximo-mcp-server/refs/heads/main/MAXMCPMETADATA.py`

Deploy steps in Maximo Administration:

1. Go to System Configuration -> Platform Configuration -> Automation Scripts
2. Create a new script named `MAXMCPMETADATA`
3. Paste the content from the URL above
4. Activate the script

---

## Installation

```bash
npm install -g @soumyaprasadrana/maximo-mcp-server
```

Verify:

```bash
maximo-mcp-server --version
maximo-mcp-server --help
```

---

## Starting the server

### Option 1: environment variables

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

### Option 2: CLI flags

```bash
maximo-mcp-server \
  --maximo-url     "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key" \
  --data-dir       /opt/maximo-mcp \
  --logs-dir       /opt/maximo-mcp/logs
```

HTTP transport with diagnostics enabled:

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

Read-only surface (query and working-set reads plus diagnostics, no write tools):

```bash
maximo-mcp-server \
  --maximo-url     "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key" \
  --data-dir       /opt/maximo-mcp \
  --logs-dir       /opt/maximo-mcp/logs \
  --readonly
```

Force a full metadata re-sync:

```bash
maximo-mcp-server \
  --maximo-url     "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key" \
  --data-dir       /opt/maximo-mcp \
  --force-reconcile
```

### Option 3: .env file

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

## Persistent storage (required)

Linux / macOS:

```bash
mkdir -p /opt/maximo-mcp/data /opt/maximo-mcp/logs
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path C:\maximo-mcp, C:\maximo-mcp\data, C:\maximo-mcp\logs
```

| Directory                 | Env var             | Contents                                   |
| ------------------------- | ------------------- | ------------------------------------------ |
| `<data-dir>/data/meta.db` | `MCP_DATA_BASE_DIR` | SQLite metadata and OAuth client database  |
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

Set `MCP_STRICT_TOOL_SCHEMA=true` when registering the server with IBM watsonx Orchestrate.
This switches all tool inputs to strict (no-nullable, no-union) JSON Schemas, which Orchestrate's
tool import requires.

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

## OAuth 2.0 setup (HTTP transport only)

When `MCP_TRANSPORT=http`, the server enforces OAuth 2.0 Bearer token authentication on every
MCP connection. Clients use the `client_credentials` grant to obtain a JWT and send it as
`Authorization: Bearer <token>`.

### Step 1: create an OAuth client

```bash
maximo-mcp-server \
  --setup-oauth \
  --data-dir /opt/maximo-mcp \
  --maximo-url "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key"
```

This prints `client_id` and `client_secret` to stdout. Save the secret; it is shown only once.
If `MCP_OAUTH_CREDS_DIR` is set, the credentials are also written to `oauth-credentials.json` in
that directory.

### Step 2: obtain a token at runtime

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

### Step 3: connect the MCP client

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
| `MCP_OAUTH_CREDS_DIR`     | (none)  | Directory where the credentials file is written |
| `MCP_SETUP_OAUTH`         | (none)  | Set to `1` to run setup-oauth mode and exit     |
| `MCP_LIST_OAUTH_CLIENTS`  | (none)  | Set to `1` to list clients and exit             |
| `MCP_DELETE_OAUTH_CLIENT` | (none)  | Set to `<clientId>` to delete a client and exit |

---

## Metadata sync

On first startup the server downloads all Maximo Object Structure metadata. This can take
several minutes on large Maximo environments. Sync is resumable: if the server restarts
mid-sync, the next startup resumes from the last completed stage.

Sync stages:

| Stage | Name                  | What it fetches                                                |
| ----- | --------------------- | -------------------------------------------------------------- |
| 1     | Fetching API metadata | List of all Object Structures from `/api/apimeta`              |
| 2     | Loading schemas       | JSON schema for each Object Structure (one request per OS)     |
| 3     | Loading MBO metadata  | Object/attribute/relationship data via `MAXMCPMETADATA` script |

While sync is running, tool calls return a `metadata_sync_in_progress` response with the current
stage and percentage. Enable `--dev-mode` and use `mcp_server_status` / `mcp_read_logs` to
monitor sync from within the agent.

### Sync startup modes

| Mode                      | Flag               | Behavior                                                                                  |
| ------------------------- | ------------------ | ----------------------------------------------------------------------------------------- |
| Fire-and-forget (default) | (none)             | Server starts immediately; sync runs in-process in the background.                        |
| Synchronous               | `--reconcile-sync` | Server blocks until sync completes before accepting connections.                          |
| Background worker         | `--bg-sync-worker` | Sync runs as a detached child process; a file lock prevents duplicate workers on restart. |

Background worker example (Claude Desktop):

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

## Configuration reference

### Required

| Variable            | CLI flag           | Description                                      |
| ------------------- | ------------------ | ------------------------------------------------ |
| `MAXIMO_URL`        | `--maximo-url`     | Base URL of the Maximo instance                  |
| `MAXIMO_API_KEY`    | `--maximo-api-key` | API key used for all Maximo calls                |
| `MCP_DATA_BASE_DIR` | `--data-dir`       | Persistent base directory (holds `data/meta.db`) |
| `MCP_LOGS_DIR`      | `--logs-dir`       | Persistent log directory                         |

### Transport

| Variable                 | CLI flag               | Default | Description                                           |
| ------------------------ | ---------------------- | ------- | ----------------------------------------------------- |
| `MCP_TRANSPORT`          | `--transport`          | `stdio` | `stdio` or `http`                                     |
| `MCP_SERVER_PORT`        | `--port`               | `8001`  | HTTP port when transport is `http`                    |
| `MCP_STRICT_TOOL_SCHEMA` | `--strict-tool-schema` | `false` | Strict (no-nullable) schemas, for watsonx Orchestrate |

### Logging

| Variable               | CLI flag             | Default | Description             |
| ---------------------- | -------------------- | ------- | ----------------------- |
| `MCP_LOG_ROTATE_DAILY` | `--log-rotate-daily` | `true`  | Rotate logs by date     |
| `MCP_LOG_MAX_MB`       | `--log-max-mb`       | `20`    | Max MB per log file     |
| `MCP_LOG_MAX_FILES`    | `--log-max-files`    | `30`    | Retained log files      |
| `MCP_LOG_TO_CONSOLE`   | `--log-to-console`   | `false` | Echo logs to console    |
| `MCP_SERVER_DEBUG`     | `--debug`            | `false` | Enable debug-level logs |

### Metadata sync

| Variable                       | CLI flag                  | Default     | Description                                 |
| ------------------------------ | ------------------------- | ----------- | ------------------------------------------- |
| `MCP_RECONCILE_ON_STARTUP`     | `--reconcile-on-startup`  | `true`      | Sync on startup                             |
| `MCP_RECONCILE_ON_RESTART`     | `--force-reconcile`       | `false`     | Force a full re-sync on every restart       |
| `MCP_RECONCILE_WEEKLY_ENABLED` | `--reconcile-weekly`      | `false`     | Weekly background re-sync                   |
| `MCP_RECONCILE_WEEKLY_CRON`    | `--reconcile-weekly-cron` | `0 3 * * 0` | Cron expression for weekly sync             |
| `MCP_RECONCILE_SYNC`           | `--reconcile-sync`        | `false`     | Block server startup until sync completes   |
| `MCP_BG_SYNC_WORKER`           | `--bg-sync-worker`        | `false`     | Spawn sync as a detached background process |

### Embeddings

| Variable              | CLI flag            | Default | Description                  |
| --------------------- | ------------------- | ------- | ---------------------------- |
| `MCP_EMBEDDINGS_MODE` | `--embeddings-mode` | `none`  | `none`, `local`, or `openai` |

`none` is recommended for production. Local embeddings require native dependencies that may not
build on every platform.

### Audit

| Variable                 | CLI flag            | Default   | Description                      |
| ------------------------ | ------------------- | --------- | -------------------------------- |
| `AUDIT_ENABLED`          | `--audit-enabled`   | `false`   | Enable Working Set audit logging |
| `AUDIT_DB_DIR`           | `--audit-dir`       | `./audit` | Monthly audit SQLite files       |
| `AUDIT_RETENTION_MONTHS` | `--audit-retention` | `12`      | Audit retention in months        |

### Diagnostics

| Variable              | CLI flag     | Default | Description             |
| --------------------- | ------------ | ------- | ----------------------- |
| `MCP_ENABLE_DEV_MODE` | `--dev-mode` | `false` | Enable diagnostic tools |

When `MCP_ENABLE_DEV_MODE=true`, two additional MCP tools are registered:

- `mcp_server_status`: a full diagnostic snapshot (sync stage/progress, database counts,
  checkpoint state, log file list)
- `mcp_read_logs`: tail recent log entries, with an optional level filter

These tools bypass the metadata sync guard, so they work even during an active sync.
`--readonly` registers them as well, without requiring `--dev-mode`.

### Read-only mode

| Variable       | CLI flag     | Default | Description                                              |
| -------------- | ------------ | ------- | -------------------------------------------------------- |
| `MCP_READONLY` | `--readonly` | `false` | Register only the Maximo read path plus diagnostic tools |

When enabled, write tools are not registered. The live surface is `maximo_get_metadata`,
`os_query_builder` (`opAction=query` only), `ws_load`, `ws_get_records`, `ws_list_attachments`,
`ws_get_attachment`, plus `mcp_server_status` and `mcp_read_logs`. Working-set writes, context
tools, audit, status/workflow, and premium configuration tools are omitted.

### Maximo Developer Copilot mode

| Variable           | CLI flag         | Default | Description                                             |
| ------------------ | ---------------- | ------- | ------------------------------------------------------- |
| `MCP_COPILOT_MODE` | `--copilot-mode` | `false` | Enables Maximo Developer Copilot discovery capabilities |

When enabled, the server exposes Migration Manager Object Structures for discovery and Working
Set edits. This mode targets coding agents that develop, configure, and validate Maximo as a
platform, using the server's existing metadata discovery, staging, preview, and commit lifecycle.

Migration Manager Object Structures must be enabled for OSLC discovery: ensure the Maximo system
property `mxe.oslc.validusewith` includes `MIGRATIONMGR`.

```text
INTEGRATION,OSLC,REPORTING,MIGRATIONMGR
```

This is an experimental feature intended for development environments. Review every Working Set
preview and validation warning before committing configuration changes.

---

## Tool reference

### Metadata and discovery

#### `maximo_get_metadata`

Resolves `maximo://` URIs for Object Structure discovery and schema lookup.

| URI pattern                                      | Returns                                                           |
| ------------------------------------------------ | ----------------------------------------------------------------- |
| `maximo://os/search/{query}`                     | Object Structures matching a keyword                              |
| `maximo://os/{osName}/schema`                    | API-scoped schema for parent object fields                        |
| `maximo://os/{osName}/relatedObjects`            | Children this OS exposes: `objectName`, `relation`, `cardinality` |
| `maximo://os/{osName}/subschemas/{childObject}`  | Child object schema                                               |
| `maximo://object/{object}/relationships/compact` | Every relationship: name, target object, join `whereClause`       |

Start here before building queries. Prefer the `maximo://os/...` URIs, which are scoped by
object-structure security. `relationships/compact` is useful mainly to name a relationship that
`relatedObjects` does not list.

#### `os_query_builder`

Builds a validated OSLC query URL and creates the Working Set session (`wsId`). This is the
standard Working Set creation path.

Supports `where` conditions, `select`, `orderBy`, `pageSize`, `childOptions`, `childCollection`,
and `savedQuery`, plus two additional parent-level filters:

- **Timeline filters** (`tlrange` / `tlattribute`): a date-math range around an index date, for
  example `tlrange="-3M"`, `tlattribute="reportdate"` for "reported in the last 3 months".
  `tlrange` follows `<sign><n><unit>`, where sign is `+`, `-`, or `+-`, and unit is one of
  `D` (days), `W` (weeks), `M` (months), `Y` (years), `h` (hours), `m` (minutes), or
  `s` (seconds). The two fields are required together.
- **Synonym-domain internal filters** (`domaininternalwhere`): filters on the internal value of
  an attribute bound to a synonym domain (for example WOSTATUS) rather than its external display
  value. Format is `<attrName>=val1,val2,...` for an IN match, or `<attrName>!=val1,val2,...`
  for a NOT IN match. It is independent of `where` and is combined with it using AND.

Related data is available three ways, and each wants a different name; the wrong one returns
empty rows rather than an error:

| Goal                                        | Use                           | Name it wants                 |
| ------------------------------------------- | ----------------------------- | ----------------------------- |
| Expand a child the OS exposes               | child block in `select`       | child object name, lowercased |
| Reach a relationship the OS does not expose | `rel.<name>{...}` in `select` | relationship name             |
| Filter, sort, or page child rows            | `childCollection`             | either, and they can differ   |

Filtering child rows requires `childCollection`; `childOptions` and dot notation cannot page or
count them (dot notation filters parents by child values, it does not trim child rows).
Aggregation is not available; `_dbcount` and similar are accepted and silently dropped, so
`collectioncount` is the only supported count.

---

### Working Set tools

A Working Set is a stateful, in-memory session tied to query context. All mutations are staged
and must be explicitly committed.

#### Read and load

| Tool             | What it does                                   |
| ---------------- | ---------------------------------------------- |
| `ws_load`        | Loads records from Maximo into the working set |
| `ws_get_records` | Returns loaded records from working set memory |
| `ws_get_active`  | Returns the current active record              |

Both `ws_load` and `ws_get_records` support `useLean=true` for a large reduction in token usage
on large result sets.

When the query sets `collectioncount: true`, `ws_load` returns `meta.totalCount` (total records
matching in Maximo), `meta.count` (rows in this page), and `meta.hasMore`. Totals survive lean
encoding, so answer "how many" from `totalCount`, never from the page length.

#### Stage changes

| Tool                 | What it does                                                             |
| -------------------- | ------------------------------------------------------------------------ |
| `ws_update_field`    | Stages one field update on one record                                    |
| `ws_multi_update`    | Stages multiple field updates across records                             |
| `ws_batch_update`    | Stages updates based on a filter/diff spec                               |
| `ws_set_active`      | Sets the active record; accepts index, `_tempId`, `restId`, or href      |
| `ws_init_new_record` | Creates a schema-based draft for a new record (create flow)              |
| `ws_update_draft`    | Merges user-supplied fields into a draft created by `ws_init_new_record` |
| `ws_delete_record`   | Stages a delete operation                                                |

#### Review and finalize

| Tool                 | What it does                                                                             |
| -------------------- | ---------------------------------------------------------------------------------------- |
| `ws_preview_changes` | Returns the staged diff plus non-blocking `validation_warnings` for review before commit |
| `ws_commit`          | Plans and applies staged changes to Maximo (validation warnings do not block commit)     |
| `ws_discard`         | Drops staged changes, keeps loaded state                                                 |
| `ws_remove`          | Removes the working set from memory (session cleanup)                                    |

`ws_preview_changes` runs a full validation pass (domain values, read-only flags, type checks)
and returns the results in `validation_warnings`; present these to the user before deciding
whether to adjust or proceed. `ws_commit` does not re-run validation; it goes directly to plan
and execute, letting Maximo act as the final authority.

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

### Business process tools

#### Status change

Status changes are executed through Maximo's `changeStatus` action, not as field updates. Use
the two-tool pattern below to enforce user review before execution.

**`maximo_plan_status_change`** validates a proposed status transition and returns a preview
without making any changes. It fetches the current status, checks `allowedactions` to confirm
`changeStatus` is permitted, and returns the current status, target status, transition verdict,
and the full allowed-actions list. Always call this first, and show the result to the user
before proceeding.

**`maximo_change_status`** executes the status transition after user confirmation. It calls
`getAllowedActions` again immediately before execution to guard against race conditions, and
rejects the request if `changeStatus` is not in the allowed actions.

Example flow:

```
1. os_query_builder -- find the work order, get wsId + restId
2. maximo_plan_status_change osName=MXAPIWO restId=12345 newStatus=CLOSE memo="Job complete"
3. -- show the plan to the user, get confirmation
4. maximo_change_status osName=MXAPIWO restId=12345 newStatus=CLOSE memo="Job complete"
```

#### Workflow

**`maximo_get_workflow_assignments`** queries the `MXAPIWFASSIGNMENT` object structure to list
pending workflow tasks. Filters: `personId`, `roleId`, `processName`, `ownerTable`, `pageSize`.
Use `includeAllowedActions=true` to fetch the allowed actions on each owning record in one call.

**`maximo_send_workflow_response`** invokes a workflow action on the owning record (work order,
service request, and so on). It calls `getAllowedActions` before execution and rejects the
request if the action is not available. Omit `actionName` to get a discovery response listing
only the allowed actions.

Common action names (these vary by workflow configuration):

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
2. -- returns ownerid=5678, ownertable=WORKORDER, _allowedActions=[wfappr, wfcanreq]
3. maximo_send_workflow_response osName=MXAPIWO restId=5678 actionName=wfappr params={memo:"Approved"}
```

---

### Context session store

Six lightweight key-value tools for storing agent state across tool calls within a conversation.

| Tool         | What it does                                        |
| ------------ | --------------------------------------------------- |
| `ctx_create` | Creates a new named session store                   |
| `ctx_get`    | Reads a value by key from a session                 |
| `ctx_set`    | Writes or overwrites a value by key                 |
| `ctx_remove` | Removes a single key from a session                 |
| `ctx_delete` | Deletes an entire session                           |
| `ctx_list`   | Lists all keys (and optionally values) in a session |

Useful for caching intermediate query results, tracking multi-step workflow state, or storing
user preferences without round-tripping to Maximo.

---

### Diagnostic tools (`--dev-mode`, or automatically with `--readonly`)

**`mcp_server_status`** returns a full diagnostic snapshot: server version, transport, PID,
uptime, live sync progress, checkpoint state, database record counts, active configuration, and
the log file list.

**`mcp_read_logs`** tails log entries from the MCP server log files.

| Parameter | Default  | Description                                                |
| --------- | -------- | ---------------------------------------------------------- |
| `lines`   | 100      | Number of recent lines to return (0 = all)                 |
| `level`   | `all`    | Filter: `all`, `info`, `warn`, `error`, `debug`            |
| `file`    | (latest) | Specific log filename (for example `mcp.2026-04-11.1.log`) |

---

## Orchestration patterns

### Pattern A: read-only analysis

```
1. maximo_get_metadata  maximo://os/search/work+order
2. maximo_get_metadata  maximo://os/{osName}/schema
3. os_query_builder     with status/priority/site filters
4. ws_load              useLean=true
5. ws_get_records       analyze and report
6. ws_remove            cleanup
```

### Pattern B: governed field update

```
1. os_query_builder
2. ws_load
3. ws_update_field / ws_multi_update / ws_batch_update
4. ws_preview_changes   -- show diff and any validation_warnings to the user
5. ws_commit            -- persist, after user confirmation
6. ws_remove
```

### Pattern C: create a new record

```
1. ws_init_new_record   osName=MXAPISR
   -- returns wsId, draftRecord skeleton, metadata
2. ws_update_draft      wsId, fields={description:"...", reportedby:"...", ...}
3. ws_preview_changes   -- review the draft and any validation_warnings
4. ws_commit            -- creates the record in Maximo
5. ws_remove
```

### Pattern D: status transition

```
1. os_query_builder            -- find the record, get restId
2. maximo_plan_status_change   osName, restId, newStatus
3. -- show the plan to the user, wait for confirmation
4. maximo_change_status        osName, restId, newStatus, memo
```

### Pattern E: workflow approval

```
1. maximo_get_workflow_assignments  personId={me} includeAllowedActions=true
2. -- identify the assignment: note ownerid, ownertable, _allowedActions
3. -- present to the user, e.g. "Work order WO-1234 is waiting for your approval"
4. maximo_send_workflow_response    osName, restId=ownerid, actionName=wfappr
```

### Pattern F: diagnose a stalled sync

```
1. mcp_server_status
   -- read sync.currentStageName, sync.progress.percentComplete
   -- read sync.checkpoint (last persisted stage)
   -- read sync.lastError
2. mcp_read_logs  level=error  lines=50
   -- look for network errors, script failures, or auth issues
```

---

## Operational notes

- First metadata sync takes several minutes on large Maximo environments; subsequent startups
  skip it once the completed flag is persisted.
- Sync is resumable: if the server stops mid-sync, the next startup resumes from the last
  completed stage.
- Always set `MCP_DATA_BASE_DIR` and `MCP_LOGS_DIR` to persistent paths outside the process
  working directory in orchestrated environments.
- `MCP_EMBEDDINGS_MODE=none` (default) is recommended for production; local embeddings require
  native dependencies that may not build on every platform.
- Lean mode (`useLean=true` on `ws_load` / `ws_get_records`) meaningfully reduces token usage on
  large result sets.
- OAuth client secrets are hashed in the SQLite database and cannot be recovered. If a secret is
  lost, delete the client and create a new one.

---

## Premium edition

The same base layer described in this document is also available as a premium edition that adds
a set of Maximo configuration-management tools: Configure Database, Admin Mode control, system
property management, read-only SQL, cache reload, automation-script invocation, Application
Designer presentation editing, and configuration safety guards. These tools are not included in
this npm package.

For access to the premium edition, or for evaluation, partnership, or a tailored build, contact
**soumyaprasad.rana@gmail.com**.

---

## Support

- GitHub issues: https://github.com/soumyaprasadrana/maximo-mcp-server/issues
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Related project: [maximo-kit](https://github.com/soumyaprasadrana/maximo-kit), a Spec Kit
  extension that drives this server through a design-first, recipe-driven configuration workflow

## Contact

**soumyaprasad.rana@gmail.com**
