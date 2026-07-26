# Tool Reference

Every tool the server exposes to MCP clients, grouped by purpose. Tool names use underscores.

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

Builds a validated OSLC query URL **and creates the Working Set** (returns `wsId`). Supports `where` (parent filters, incl. dot-notation on children), `childOptions` (which child rows appear), `select`, `orderBy`, `pageSize`, `savedQuery`, and full-text `searchTerms`. 

Advanced: Use `rawWhere` and `rawSelect` to pass raw OSLC strings when the structured schema doesn't fit complex expressions.

This is the official path to create a Working Set.

## Working Set — read & load

| Tool | What it does |
| --- | --- |
| `ws_load` | Loads records from Maximo into the Working Set (`useLean` supported) |
| `ws_get_records` | Returns already-loaded records from memory (`useLean` supported) |
| `ws_get_active` | Returns the current active record |
| `ws_set_active` | Sets the active record — by index, `_tempId`, restId, or href |

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
| `ws_commit` | Plan and apply staged changes to Maximo |
| `ws_discard` | Drop staged changes, keep loaded records |
| `ws_remove` | Remove the Working Set from memory (session cleanup) |

## Attachments

| Tool | What it does |
| --- | --- |
| `ws_list_attachments` | List a record's doclinks |
| `ws_get_attachment` | Fetch attachment content by identifier or href |

## Business process

| Tool | What it does |
| --- | --- |
| `maximo_plan_status_change` | Validate a status transition and preview it (no change). **Call first.** |
| `maximo_change_status` | Execute the transition after confirmation (re-checks allowed actions) |
| `maximo_get_workflow_assignments` | List pending workflow tasks (filter by person, role, process…) |
| `maximo_send_workflow_response` | Invoke a workflow action (approve/reject/…) on the owning record |

Common workflow actions: `wfappr` (approve), `wfreject` (reject), `wfcanreq` (cancel), `wfaccept` (accept), `wfreturn` (return for rework) — exact names vary by configuration.

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

## Dev diagnostics *(requires `MCP_ENABLE_DEV_MODE=true`)*

| Tool | What it does |
| --- | --- |
| `mcp_server_status` | Full diagnostic snapshot — version, transport, sync progress, checkpoints, DB counts, logs |
| `mcp_read_logs` | Tail log entries with optional level filter |

These bypass the metadata-sync guard, so they work during an active sync.
