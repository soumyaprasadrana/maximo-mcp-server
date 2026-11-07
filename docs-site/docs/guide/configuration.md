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

## Electronic signature (optional)

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MAXIMO_ESIG_AUTH` | -- | *(unset)* | Service-account electronic signature for `maximo_change_status`: base64 of the **password only** (not `userid:password`) for the user behind `MAXIMO_API_KEY` |

Maximo can require an electronic signature (a SIGOPTION setting) before certain actions, such as a
status change. `maximo_change_status` always asks Maximo to enforce it. When
`MAXIMO_ESIG_AUTH` is set, the server supplies the signature itself and callers only need to give a
reason; use this when many chat users share one service account and none of them knows its
password. A caller-supplied `esigAuth` always overrides it. If it is unset, a required signature
fails with `error.reason: "esig_required"` and the caller supplies `esigAuth` and `esigReason`. If the
configured value is rejected, the error is `esig_invalid_server_credential` (an operator fix).

## Transport

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_TRANSPORT` | `--transport` | `stdio` | `stdio` or `http` |
| `MCP_SERVER_PORT` | `--port` | `8001` | HTTP port when `transport=http` |
| `MCP_SERVER_HOST` | `--host` | *(all interfaces)* | HTTP bind address, e.g. `127.0.0.1` to accept local connections only |
| `MCP_CALLER_APIKEY` | `--caller-apikey` | `false` | HTTP transport: run each request as the Maximo user whose API key is in the `x-maximo-apikey` header. Requests without it use `MAXIMO_API_KEY` (always used for metadata). Working sets become private to their creator |
| `MCP_STRICT_TOOL_SCHEMA` | `--strict-tool-schema` | `false` | Strict (no nullable/union) schemas for IBM watsonx Orchestrate |

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
| `MCP_RECONCILE_LAZY` | `--reconcile-lazy` | `false` | On-demand metadata: no startup sync; fetch each object structure on first use |
| `MCP_RECONCILE_LAZY_TTL` | `--reconcile-lazy-ttl` | `86400` | Seconds before on-demand metadata is refetched |
| `MCP_RECONCILE_LAZY_CATALOG_TTL` | `--reconcile-lazy-catalog-ttl` | `3600` | Seconds before the object structure list is refetched |
| `MCP_RECONCILE_LAZY_NEGATIVE_TTL` | `--reconcile-lazy-negative-ttl` | `300` | Seconds a not-found or failed fetch is remembered |

With `MCP_RECONCILE_LAZY=true` the server starts in seconds and fetches each object structure's
metadata the first time a tool needs it, caching it in the same database until the TTL expires.
`--force-reconcile` and the weekly cron then expire the cache instead of reloading. See
[Metadata Engine](/concepts/metadata-engine#on-demand-mode).

## Embeddings

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_EMBEDDINGS_MODE` | `--embeddings-mode` | `none` | `none` or `local` |

::: tip
`none` (keyword search) is the default and recommended. `local` needs `@xenova/transformers`, which is not bundled (its native binaries fail to install on some machines): install it yourself next to the server, e.g. `npm install -g @xenova/transformers`. Without it the server logs a hint and uses keyword search.
:::

## Async commit

| Variable | Default | Description |
| --- | --- | --- |
| `MCP_ASYNC_COMMIT_OS` | `DMMAXOBJECTCFG` | Comma-separated Object Structures whose `ws_commit` runs as a background job. Set to an empty string to make every commit synchronous. |
| `MCP_ASYNC_COMMIT_RETENTION_MS` | `1800000` | How long a finished commit job stays pollable by `ws_commit_status` (30 minutes). |

See [Async Commit](/guide/async-commit) for the start/poll contract.

## HTTP transport and timeouts

Outbound calls use two connection pools. Configuration writes (create, update, delete, sync,
bulk) go through a long-operation pool with no per-phase timeout, bounded by an absolute
deadline; reads keep a protective per-phase timeout so a wedged request cannot hang forever.

| Variable | Default | Description |
| --- | --- | --- |
| `MAXIMO_COMMIT_TIMEOUT_MS` | `900000` | Total wall-clock budget for one configuration write (15 minutes). Raise it if your instance needs longer for large object creates. |
| `MAXIMO_HTTP_TIMEOUT_MS` | `300000` | Per-phase timeout for ordinary reads, metadata, and lookups. |
| `MAXIMO_MAX_CONNECTIONS` | `32` | Maximum simultaneous connections per origin, across both pools. |

::: warning Why this exists
Node's global `fetch()` caps every request at a 300s undici `headersTimeout` that cannot be
raised from the call site. Long `DMMAXOBJECTCFG` commits were being cut off mid-flight while
Maximo kept working, surfacing only as `TypeError: fetch failed`. If you ever see a commit fail
at almost exactly 300s with `UND_ERR_HEADERS_TIMEOUT`, the server is running without its
dispatcher (check the startup log for an `undici unavailable` warning).
:::

## Working sets

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_WS_PERSIST` | `--ws-persist` | `false` | Keep working sets in `<data-dir>/data/workingsets.db` so they survive a restart |
| `MCP_WS_TTL_MINUTES` | `--ws-ttl-minutes` | `15` | Idle minutes before a working set expires |
| `MCP_WS_PERSIST_MAX_MB` | `--ws-persist-max-mb` | `64` | Largest working set (serialized MB) that is persisted; bigger ones stay in memory only |
| `MCP_WS_SWEEP_SECONDS` | `--ws-sweep-seconds` | `60` | How often expired working sets are removed and the store shrunk (5..3600) |

With `MCP_WS_PERSIST=true`, loaded records and staged changes survive a server restart; see
[Working Set Model](/concepts/working-set#persistence). `workingsets.db` holds business data, so
protect the data directory. Expired entries are removed automatically and the file shrinks back
after bursts; the server warns at startup if persistence is off but the file still exists.

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
| `MCP_ENABLE_DEV_MODE` | `--dev-mode` | `false` | Register `mcp_read_logs` |

`mcp_server_status` is always registered. Dev mode adds `mcp_read_logs` (this server's own log); both bypass the metadata-sync guard so they work even during an active sync.

## Readonly mode

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_READONLY` | `--readonly` | `false` | Register only the Maximo read path plus MCP diagnostics |
| `MCP_ENABLE_SCRIPT_GET` | `--enable-script-get` | `false` | With `--readonly`, also register `maximo_invoke_automation_script` in a GET-only form |

When on, write tools are not registered. The live surface is:

- `maximo_get_metadata`
- `os_query_builder` (`opAction=query` only; update/patch/delete are rejected)
- `ws_load`, `ws_next_page`, `ws_previous_page`, `ws_get_records`, `ws_remove`, `ws_get_allowed_actions`
- `ws_list_attachments`, `ws_get_attachment`
- `maximo_get_allowed_actions`
- `maximo_get_url` (GET-only, same-host, refuses `action=` and script paths)
- `maximo_get_workflow_assignments`, `maximo_lookup_values`, `maximo_aggregate`
- `maximo_list_reports`, `maximo_run_report`, `maximo_integration_errors`
- `maximo_read_server_log` when `MCP_ENABLE_SERVER_LOGS` is set
- `mcp_server_status`, `mcp_read_logs` (no `--dev-mode` required)

Working-set writes, ctx tools, audit, status changes, workflow routing, attachments upload, import, action/script invocation, and configuration tools are omitted.

`MCP_ENABLE_SCRIPT_GET` is an explicit opt-in: it adds `maximo_invoke_automation_script` to the
read-only surface with GET only (no method choice, no request body). It is off by default because
Maximo does not stop a script from changing data on a GET -- enable it only if the scripts the API
user can reach are safe for a read-only deployment. No effect without `--readonly`.

## Tool exposure

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_COPILOT_AUTO_PROVISION` | `--copilot-auto-provision` | `false` | With `--copilot-mode`, install the copilot utilities at startup (writes to Maximo) |
| `MCP_DISABLED_TOOLS` | `--disabled-tools` | *(empty)* | Comma-separated tools never to register, in any mode. A trailing `*` matches a prefix (`ws_commit*`); case is ignored |
| `MCP_ENABLE_SERVER_LOGS` | `--enable-server-logs` | `false` | Register `maximo_read_server_log` (Maximo's own Liberty log -- contains other users' data). Never registered with `--caller-apikey` |

A disabled tool is absent from `tools/list`. An entry that matches no tool is logged at startup and
listed by `mcp_server_status` under `toolRestrictions.unmatchedPatterns`, so a typo does not leave a
tool exposed unnoticed.

The tools that run automation scripts inside Maximo -- `maximo_copilot_setup`,
`maximo_dbconfig_status`, `maximo_dbconfig_apply_status`, `maximo_dbconfig_discard`,
`maximo_dbconfig_apply`, `maximo_admin_mode`, `maximo_sql_query`, `maximo_system_property` and
`maximo_reload_cache` -- and `maximo_appdesigner_edit`, which writes through `DMMAXAPPS`, are
registered only with `MCP_COPILOT_MODE=true`, whatever this list says.

```bash
# example: a business-data server without file import and without commits
MCP_DISABLED_TOOLS=maximo_import_file*,ws_commit*
```

## Limits

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_MAX_PAGE_SIZE` | `--max-page-size` | `1000` | Largest `os_query_builder` pageSize; larger values are clamped with a warning |
| `MCP_MAX_ATTACHMENT_MB` | `--max-attachment-mb` | `25` | Largest attachment downloaded or uploaded |
| `MCP_MAX_REPORT_MB` | `--max-report-mb` | `10` | Largest BIRT report returned |
| `MCP_SERVER_LOG_SCAN_MB` | `--server-log-scan-mb` | `64` | Most of Maximo's messages.log scanned per `maximo_read_server_log` call |
| `MCP_MAX_CONCURRENT_TOOL_CALLS` | `--max-concurrent-tool-calls` | `0` (unlimited) | Parallel tool calls before the server answers `server_busy` |

## Maximo Developer Copilot mode

| Variable | CLI flag | Default | Description |
| --- | --- | --- | --- |
| `MCP_COPILOT_MODE` | `--copilot-mode` | `false` | Experimental Maximo Developer Copilot capabilities, including the automation-script tools ([Copilot Tools](/tools/copilot)) |

When `MCP_COPILOT_MODE=true`, the server enables experimental capabilities using **Migration Manager** Object Structures — intended for coding agents (Claude, Cursor) to develop, configure, and validate Maximo as a platform, using the same discover → stage → preview → approve → commit lifecycle.

Migration Manager Object Structures must be enabled for OSLC discovery. Ensure the Maximo system property `mxe.oslc.validusewith` includes `MIGRATIONMGR`:

```text
INTEGRATION,OSLC,REPORTING,MIGRATIONMGR
```

::: warning Experimental
Use only in development environments. Review every Working Set preview and validation warning before committing configuration changes.
:::
