# Configuration Reference

Every setting can be provided as an **environment variable** or an equivalent **CLI flag**. CLI flags take precedence.

## Required

| Variable | CLI flag | Description |
| --- | --- | --- |
| `MAXIMO_URL` | `--maximo-url` | Base URL of the Maximo instance |
| `MAXIMO_API_KEY` | `--maximo-api-key` | API key used for all Maximo calls |
| `MCP_DATA_BASE_DIR` | `--data-dir` | Persistent base dir (holds `data/meta.db`) |
| `MCP_LOGS_DIR` | `--logs-dir` | Persistent log directory |

`MAXIMO_METADATA_API_KEY` may be set separately if the metadata endpoints use a different key.

## Transport

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_TRANSPORT` | `--transport` | `stdio` | `stdio` or `http` |
| `MCP_SERVER_PORT` | `--port` | `8001` | HTTP port when `transport=http` |
| `MCP_STRICT_TOOL_SCHEMA` | — | `false` | Strict (no nullable/union) schemas for IBM watsonx Orchestrate |

## Logging

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_LOG_ROTATE_DAILY` | `--log-rotate-daily` | `true` | Rotate logs by date |
| `MCP_LOG_MAX_MB` | `--log-max-mb` | `20` | Max MB per log file |
| `MCP_LOG_MAX_FILES` | `--log-max-files` | `30` | Retained log files |
| `MCP_LOG_TO_CONSOLE` | `--log-to-console` | `false` | Echo logs to console |
| `MCP_SERVER_DEBUG` | `--debug` | `false` | Enable debug-level logs |

## Metadata sync

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_RECONCILE_ON_STARTUP` | `--reconcile-on-startup` | `true` | Sync on startup |
| `MCP_RECONCILE_ON_RESTART` | `--force-reconcile` | `false` | Force a full re-sync every restart |
| `MCP_RECONCILE_WEEKLY_ENABLED` | `--reconcile-weekly` | `false` | Weekly background re-sync |
| `MCP_RECONCILE_WEEKLY_CRON` | `--reconcile-weekly-cron` | `0 3 * * 0` | Cron for weekly sync |
| `MCP_RECONCILE_SYNC` | `--reconcile-sync` | `false` | Block startup until sync completes |
| `MCP_BG_SYNC_WORKER` | `--bg-sync-worker` | `false` | Spawn sync as a detached process |

## Embeddings

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_EMBEDDINGS_MODE` | `--embeddings-mode` | `none` | `none`, `local`, or `openai` |

::: tip
`none` is recommended for production. Local embeddings need native dependencies that may not build on every platform.
:::

## Audit

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `AUDIT_ENABLED` | `--audit-enabled` | `false` | Enable Working Set audit logging |
| `AUDIT_DB_DIR` | `--audit-dir` | `./audit` | Monthly audit SQLite files |
| `AUDIT_RETENTION_MONTHS` | `--audit-retention` | `12` | Audit retention in months |

Additional tuning: `AUDIT_FLUSH_INTERVAL_MS`, `AUDIT_BATCH_SIZE`.

## OAuth 2.0 (HTTP transport)

| Variable | Default | Description |
| --- | --- | --- |
| `MCP_OAUTH_TOKEN_TTL` | `3600` | JWT expiry in seconds |
| `MCP_OAUTH_CREDS_DIR` | — | Directory where the credentials file is written on client creation |
| `MCP_SETUP_OAUTH` | — | Set to `1` to run setup-oauth mode and exit |
| `MCP_LIST_OAUTH_CLIENTS` | — | Set to `1` to list clients and exit |
| `MCP_DELETE_OAUTH_CLIENT` | — | Set to `<clientId>` to delete a client and exit |

See [Connecting Clients → HTTP + OAuth](/guide/clients#http-transport-with-oauth-2-0).

## Dev mode

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_ENABLE_DEV_MODE` | `--dev-mode` | `false` | Register diagnostic tools |

When enabled, two extra tools appear — `mcp_server_status` and `mcp_read_logs` — which bypass the metadata-sync guard so they work even during an active sync.

## Maximo Developer Copilot mode

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_COPILOT_MODE` | `--copilot-mode` | `false` | Experimental Maximo Developer Copilot capabilities |

When `MCP_COPILOT_MODE=true`, the server enables experimental capabilities using **Migration Manager** Object Structures — intended for coding agents (Claude, Cursor) to develop, configure, and validate Maximo as a platform, using the same discover → stage → preview → approve → commit lifecycle.

Migration Manager Object Structures must be enabled for OSLC discovery. Ensure the Maximo system property `mxe.oslc.validusewith` includes `MIGRATIONMGR`:

```text
INTEGRATION,OSLC,REPORTING,MIGRATIONMGR
```

::: warning Experimental
Use only in development environments. Review every Working Set preview and validation warning before committing configuration changes.
:::
