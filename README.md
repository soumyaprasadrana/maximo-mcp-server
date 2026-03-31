# maximo-mcp-server

[![npm version](https://img.shields.io/npm/v/@soumyaprasadrana/maximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/%40soumyaprasadrana%2Fmaximo-mcp-server.svg)](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server)
[![Node.js](https://img.shields.io/badge/node-%3E%3D20-339933.svg)](https://nodejs.org)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](./LICENSE)
[![Repository](https://img.shields.io/badge/repo-github-black.svg)](https://github.com/soumyaprasadrana/maximo-mcp-server)

Enterprise MCP server for IBM Maximo Application Suite.

This server provides a governed interface between AI agents and Maximo by combining metadata-aware query construction with a Working Set transaction model for safe, reviewable changes.

## Why This Exists

Direct LLM-to-Maximo API access is risky in enterprise systems:

- Object Structure selection is non-trivial.
- Schema context is too large for naive prompting.
- Mutations need controlled staging and explicit commit gates.

`maximo-mcp-server` solves this by making Object Structures and metadata first-class, and by forcing staged updates before writes.

## Architecture

```text
AI Agent (MCP Client)
        |
        | MCP (stdio/http)
        v
maximo-mcp-server
  |- Metadata Engine (SQLite-backed)
  |- OS Query Builder
  |- Working Set Engine (stage/preview/commit/discard)
        |
        v
IBM Maximo REST / OSLC APIs
```

## Installation

Run directly with `npx`:

```bash
npx -y @soumyaprasadrana/maximo-mcp-server
```

Or install globally:

```bash
npm i -g @soumyaprasadrana/maximo-mcp-server
maximo-mcp-server
```

Default transport is `stdio`.

## HTTP Mode

```bash
MCP_TRANSPORT=http \
MCP_SERVER_PORT=8001 \
MAXIMO_URL="https://your-maximo-host/maximo" \
MAXIMO_API_KEY="your-api-key" \
npx -y @soumyaprasadrana/maximo-mcp-server
```

Exposed endpoints:

- `POST /mcp`
- `GET /health`

## Configuration

### Required

| Variable         | Description                  |
| ---------------- | ---------------------------- |
| `MAXIMO_URL`     | Base URL of Maximo instance  |
| `MAXIMO_API_KEY` | API key used by server calls |

### Common Optional

| Variable                       | Default     | Description                         |
| ------------------------------ | ----------- | ----------------------------------- |
| `MCP_TRANSPORT`                | `stdio`     | `stdio` or `http`                   |
| `MCP_SERVER_PORT`              | `8001`      | HTTP port when `MCP_TRANSPORT=http` |
| `MCP_DATA_BASE_DIR`            | process cwd | Base directory for `data/meta.db`   |
| `MCP_RECONCILE_ON_STARTUP`     | `true`      | Metadata reconcile on startup       |
| `MCP_RECONCILE_WEEKLY_ENABLED` | `false`     | Weekly background reconcile         |
| `AUDIT_ENABLED`                | `false`     | Working Set audit logging           |

## Tooling Model

Recommended sequence:

1. `maximo_get_metadata` for Object Structure and schema discovery
2. `os_query_builder` to create validated OSLC query + Working Set
3. `ws_load` / `ws_get_records` for reads
4. `ws_update_field` / `ws_multi_update` / `ws_batch_update` for staging
5. `ws_preview_changes` then `ws_commit` (or `ws_discard`)

Working Set creation policy:

- `ws_create` is deprecated/removed for agent usage.
- Use `os_query_builder` to create Working Sets.

## Runtime Notes

- `better-sqlite3` is installed for the target OS/architecture during npm install.
- `@xenova/transformers` model assets are downloaded on first semantic-search usage.
- First metadata reconciliation time depends on Maximo metadata size.

## Security Posture

- Object-Structure-scoped access model
- Staged mutation with preview-before-commit
- No credentials baked into package artifacts

## Support

GitHub issues: https://github.com/soumyaprasadrana/maximo-mcp-server/issues

## License

Proprietary software.

- `package.json` uses: `SEE LICENSE IN LICENSE`
- Terms: [LICENSE](./LICENSE)
