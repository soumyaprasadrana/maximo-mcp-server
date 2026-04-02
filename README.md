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

Verify:

```bash
node -v
npm -v
```

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

## Configuration

### Required

| Variable | Description |
|---|---|
| `MAXIMO_URL` | Base URL of Maximo instance |
| `MAXIMO_API_KEY` | API key used by server calls |

### Common Optional

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `MCP_SERVER_PORT` | `8001` | HTTP port when `MCP_TRANSPORT=http` |
| `MCP_DATA_BASE_DIR` | process cwd | Base directory for `data/meta.db` |
| `MCP_RECONCILE_ON_STARTUP` | `true` | Reconcile metadata on startup |
| `MCP_RECONCILE_WEEKLY_ENABLED` | `false` | Weekly background reconcile |
| `MCP_EMBEDDINGS_MODE` | `none` | `none`, `local`, or `openai` |
| `AUDIT_ENABLED` | `false` | Working Set audit logging |

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

| Tool | What it does | Notes |
|---|---|---|
| `ws_load` | Loads records from Maximo into the working set | Supports `useLean=true` compression mode |
| `ws_get_records` | Returns loaded records from working set memory | Supports `useLean=true` |
| `ws_get_active` | Returns current active record | For guided record-level updates |

### Update and Stage Changes

| Tool | What it does | Notes |
|---|---|---|
| `ws_update_field` | Stages one field update on one record | No immediate Maximo mutation |
| `ws_multi_update` | Stages multiple field updates across records | Batch style for known targets |
| `ws_batch_update` | Stages updates based on filter/diff spec | Useful for many-record transformations |
| `ws_set_active` | Sets active record by restID | Simplifies sequential updates |
| `ws_init_new_record` | Creates schema-based draft for new resource | Returns metadata + draft skeleton |
| `ws_add_record` | Stages a new record insertion | Commit required to persist |
| `ws_delete_record` | Stages a delete operation | Commit required to persist |

### Review and Finalize

| Tool | What it does | Notes |
|---|---|---|
| `ws_preview_changes` | Returns staged diff (create/update/delete) | Review point before commit |
| `ws_commit` | Validates and applies staged changes to Maximo | Explicit write boundary |
| `ws_discard` | Drops all staged changes | Keeps original loaded state |
| `ws_remove` | Removes working set from memory | Session cleanup |

### Attachments

| Tool | What it does |
|---|---|
| `ws_list_attachments` | Lists record doclinks in working set context |
| `ws_get_attachment` | Retrieves attachment content by identifier or href |

### Audit

| Tool | What it does |
|---|---|
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
    "fields": ["wonum", "description", "status", "wopriority", "siteid", "owner", "reportdate"]
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
