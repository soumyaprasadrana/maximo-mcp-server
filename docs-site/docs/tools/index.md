# Tool Reference

Every tool the server exposes to MCP clients, grouped by purpose. Tool names use underscores.

::: tip Configuration tooling
Configure Database, Admin Mode, system properties, read-only SQL diagnostics and live cache reload
are in **[Copilot Tools](/tools/copilot)**. They ship in the npm package like everything else and,
with `maximo_appdesigner_edit` below, are registered only with `--copilot-mode`. Any tool can be hidden with
`MCP_DISABLED_TOOLS`. See [Versions and access](/versions).
:::

::: tip Read-only mode
With `--readonly` the server registers only: `maximo_get_metadata`, `os_query_builder` (query only),
`ws_load`, `ws_next_page`, `ws_previous_page`, `ws_get_records`, `ws_remove`, `ws_get_allowed_actions`,
`ws_list_attachments`, `ws_get_attachment`, `maximo_get_allowed_actions`, `maximo_get_url`,
`maximo_get_workflow_assignments`, `maximo_lookup_values`, `maximo_aggregate`, `maximo_list_reports`, `maximo_run_report`, `maximo_integration_errors`, plus the two diagnostics (and `maximo_read_server_log` when opted in). Everything else on this page is omitted. (Optional:
`MCP_ENABLE_SCRIPT_GET` adds a GET-only `maximo_invoke_automation_script`.)
:::

## Metadata & discovery

### `maximo_get_metadata`

Resolves `maximo://` URIs for Object Structure discovery and schema lookup. **Always start here** before building queries.

| URI pattern | Returns |
| --- | --- |
| `maximo://os/search/{query}` | Object Structures matching a keyword |
| `maximo://os/{osName}/schema` | API-scoped parent-object schema |
| `maximo://os/{osName}/relatedObjects` | Child relationships + object names |
| `maximo://os/{osName}/subschemas/{childObject}` | Child object schema (comma-separate for many) |

### `os_query_builder`

Builds a validated OSLC query URL **and creates the Working Set** (returns `wsId`). Supports `where` (parent filters, incl. dot-notation on children), `childOptions` (filters/sorts child rows already reached via `select` -- add `path` for anything nested past one relationship hop), `select`, `orderBy`, `pageSize`, `savedQuery`, and full-text `searchTerms`. 

Also accepts `pageno`, `collectioncount`, `count` (Maximo runs `SELECT COUNT(*)` and returns only `{totalCount}` -- the cheapest total), `ignorecollectionref` (drops `*_collectionref` child hrefs for smaller payloads), `addschema`, timeline filters (`tlrange`/`tlattribute`) and SynonymDomain internal filters (`domaininternalwhere`).

Advanced: Use `rawWhere` and `rawSelect` to pass raw OSLC strings when the structured schema doesn't fit complex expressions.

This is the official path to create a Working Set.

## Working Set — read & load

| Tool | What it does |
| --- | --- |
| `ws_load` | Loads records from Maximo into the Working Set (`useLean` supported). `meta.paging` reports page number, total pages and next/previous links when Maximo returns them |
| `ws_next_page` | Loads the next page of the same query into the Working Set (follows Maximo's own `nextPage` link; needs `collectioncount:true` on the query) |
| `ws_previous_page` | Loads the previous page of the same query |
| `ws_get_records` | Returns already-loaded records from memory (`useLean` supported) |
| `ws_get_active` | Returns the current active record |
| `ws_set_active` | Sets the active record — by index, `_tempId`, restId, or href |
| `ws_get_allowed_actions` | Allowed actions for **every** record the Working Set's query matches, in one call |

## Working Set — stage changes

| Tool | What it does |
| --- | --- |
| `ws_update_field` | Stage one field update on one record |
| `ws_multi_update` | Stage multiple field updates across records |
| `ws_batch_update` | Stage updates via a filter/diff spec |
| `ws_init_new_record` | Create a schema-based draft for a new record (create flow) |
| `ws_update_draft` | Merge fields into a draft from `ws_init_new_record` (child arrays supported) |
| `ws_add_child_record` | Append one child row to a relation-typed array — no full-array resubmit |
| `ws_remove_child_record` | Remove one child row by natural-key values or index |
| `ws_delete_record` | Stage a record delete |

→ Child tooling is explained in [Child Records](/concepts/child-records).

## Working Set — review & finalize

| Tool | What it does |
| --- | --- |
| `ws_preview_changes` | Staged diff + non-blocking `validation_warnings` |
| `ws_commit` | Plan and apply staged changes to Maximo — [async for slow object structures](/guide/async-commit) |
| `ws_commit_status` | Poll a background commit by `asyncId` (or Working Set id) |
| `ws_discard` | Drop staged changes, keep loaded records |
| `ws_remove` | Remove the Working Set from memory (session cleanup) |

## Application Designer

*Registered only with `--copilot-mode`.* Edit an existing app's presentation (the `MAXPRESENTATION` CLOB on `DMMAXAPPS`) by **delta**,
without shipping the 70KB+ document through the tool channel. Every control has a unique `id`,
so you send only an anchored fragment; the server holds the full CLOB.

| Tool | What it does |
| --- | --- |
| `maximo_appdesigner_edit` | Delta edit lifecycle via one `action`: `init` (open a session for an app) → `modify` (insert/replace/remove a control fragment anchored on a unique id) → `preview` (compact diff, never the full CLOB) → `commit` (stage one `MAXPRESENTATION` Change + commit through the Working Set gates; needs `confirm:true`) → `verify` (re-read and confirm). A full server restart is still required before the change surfaces in the UI. |

## Attachments

| Tool | What it does |
| --- | --- |
| `ws_list_attachments` | List a record's doclinks |
| `ws_get_attachment` | Fetch attachment content by identifier or href |
| `ws_add_attachment` | Attach a file (text or base64) to a record -- not staged, Maximo stores it on confirm. Plan first, then `confirm` |

## Business process

| Tool | What it does |
| --- | --- |
| `maximo_plan_status_change` | Validate a status transition and preview it (no change): allowed action plus Maximo's `valid_next_statuses`. **Call first.** |
| `maximo_change_status` | Execute the transition after confirmation (re-checks the allowed action and refuses a target that is not a valid next status) |
| `maximo_get_workflow_assignments` | OPEN workflow assignments with their routes (`onAccept` / `onReject`) and owning record *(read-only)* |
| `maximo_complete_workflow_assignment` | Route an assignment: `accepted` true (positive) or false (negative), with memo. Plan first, then `confirm` |
| `maximo_start_workflow` | Start a workflow process on a record. Plan first, then `confirm` |
| `maximo_send_workflow_response` | Invoke an allowed action on the owning record (workflows that expose actions there) |

`maximo_change_status` always asks Maximo to enforce any configured **electronic signature**. If one is required and none is available it fails with `error.reason: "esig_required"`; retry with `esigAuth` (base64 of the password only) and `esigReason`, or have the operator set `MAXIMO_ESIG_AUTH` on the server so callers are only asked for a reason. See [Configuration](/guide/configuration).

When routing reaches an INPUT node, Maximo keeps the choice in an interactive login session that API-key calls do not have: the tool answers `input_node_reached` with the choices and the assignment stays open -- finish it in the Maximo Inbox.

## Lookups, aggregation and reports *(read-only)*

| Tool | What it does |
| --- | --- |
| `maximo_lookup_values` | Values Maximo's lookup offers for one field -- TABLE domains (asset, location, work type, crew...) and synonym/ALN domains; for `status` on an existing record, the valid next statuses |
| `maximo_aggregate` | GROUP BY with count / sum / avg / min / max, computed by Maximo (`where` filters first) |
| `maximo_list_reports` | BIRT reports of an object structure's application |
| `maximo_run_report` | Run a report; the file (PDF by default) comes back as an embedded resource |

## Maximo diagnostics *(read-only)*

| Tool | What it does |
| --- | --- |
| `maximo_integration_errors` | Integration failures: Message Reprocessing (`errors`) or Message Tracking (`tracking`), counts per interface plus latest rows |
| `maximo_read_server_log` | Tail of Maximo's own Liberty log, filtered by level / text / time. **Opt-in** (`MCP_ENABLE_SERVER_LOGS`); needs the STREAMLOG option of LOGGING; withheld with `--caller-apikey` |

## Generic actions

| Tool | What it does |
| --- | --- |
| `maximo_get_allowed_actions` | Every action Maximo allows on one record, with each action's HTTP method and expected request body / query parameters *(read-only)* |
| `maximo_invoke_action` | Invoke any allowed action by name on one record (re-checks it is still allowed first) |

## File import

| Tool | What it does |
| --- | --- |
| `maximo_import_file` | Upload CSV (FLAT) or XML through an object structure. **Preview by default** (validates, writes nothing); `preview:false` commits; `async:true` queues large loads |
| `maximo_import_file_status` | Poll an async import using the `statusUrl` it returned |

## Automation scripts

| Tool | What it does |
| --- | --- |
| `maximo_invoke_automation_script` | Run an automation script by name (`/api/script/<name>`, GET or POST) and return its status and body. No preview -- only invoke scripts you trust. Hidden under `--readonly` unless `MCP_ENABLE_SCRIPT_GET` is set, which registers a GET-only form |

## Generic URL read

| Tool | What it does |
| --- | --- |
| `maximo_get_url` | GET any URL on the configured Maximo and return the raw response *(read-only)*. Same host only, no redirects, credential headers refused, and `action=` / `/api/script` targets refused -- use the tools above for those |

## Audit

| Tool | What it does |
| --- | --- |
| `maximo_get_audit_logs` | Fetch Working Set audit events (needs `AUDIT_ENABLED=true`) |

## Context session store

Lightweight key-value state scoped to a conversation — no round-trip to Maximo.

| Tool | What it does |
| --- | --- |
| `ctx_create` | Create a named session store |
| `ctx_get` | Read a value by key |
| `ctx_set` | Write / overwrite a value by key |
| `ctx_remove` | Remove a single key |
| `ctx_delete` | Delete an entire session |
| `ctx_list` | List keys (and optionally values) |

## MCP server diagnostics

| Tool | What it does |
| --- | --- |
| `mcp_server_status` | Full diagnostic snapshot -- version, transport, sync progress, checkpoints, DB counts, withheld tools, logs. **Always registered** |
| `mcp_read_logs` | Tail this server's own log (at most 5000 lines). Needs `MCP_ENABLE_DEV_MODE=true` (automatic with `--readonly`); withheld with `--caller-apikey` |

These bypass the metadata-sync guard, so they work during an active sync.
