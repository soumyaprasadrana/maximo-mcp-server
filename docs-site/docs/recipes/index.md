# Orchestration Patterns

Reusable tool sequences for common agent tasks. Each ends by freeing the session with `ws_remove`.

## Pattern A — Read-only analysis

```
1. maximo_get_metadata  maximo://os/search/work+order
2. maximo_get_metadata  maximo://os/{osName}/schema
3. os_query_builder     with status / priority / site filters
4. ws_load              useLean=true
5. ws_get_records       analyze and report
6. ws_remove            cleanup
```

## Pattern B — Governed field update

```
1. os_query_builder
2. ws_load
3. ws_update_field / ws_multi_update / ws_batch_update
4. ws_preview_changes   → show diff + validation_warnings to the user
5. ws_commit            → persist (after user confirms)
6. ws_remove
```

## Pattern C — Create a new record

```
1. ws_init_new_record   osName=MXAPISR
   → returns wsId, a draft skeleton, and metadata
2. ws_update_draft      wsId, fields={ description:"…", reportedby:"…", … }
3. ws_preview_changes   → review draft + validation_warnings
4. ws_commit            → creates the record in Maximo
5. ws_remove
```

## Pattern D — Edit a child collection

```
1. maximo_get_metadata  maximo://os/{osName}/relatedObjects   (find the child field)
2. os_query_builder     select the parent + child rows
3. ws_load
4. ws_set_active        <the parent record>
5. ws_add_child_record     field=<child>, record={…}
   ws_remove_child_record  field=<child>, keyValues={…}   (or index)
6. ws_preview_changes   → shows only changed rows, each with its _action
7. ws_commit
8. ws_remove
```

See [Child Records](/concepts/child-records) for how the Add/Change/Delete diff is computed.

## Pattern E — Status transition

```
1. os_query_builder            → find the record, get restId
2. maximo_plan_status_change   osName, restId, newStatus
3. → show the plan to the user, wait for confirmation
4. maximo_change_status        osName, restId, newStatus, memo
```

## Pattern F — Workflow approval

```
1. maximo_get_workflow_assignments  personId={me} includeAllowedActions=true
2. → identify assignment: ownerid + ownertable + _allowedActions
3. → present to the user: "WO-1234 is waiting for your approval"
4. maximo_send_workflow_response    osName, restId=ownerid, actionName=wfappr
```

## Pattern G — Diagnose a stalled sync *(dev mode)*

```
1. mcp_server_status
   → read sync.currentStageName, sync.progress.percentComplete
   → read sync.checkpoint (last persisted stage) and sync.lastError
2. mcp_read_logs  level=error  lines=50
   → look for network errors, script failures, or auth issues
```

## Operational notes

- First metadata sync takes 3–6 minutes on large environments; later startups skip it.
- Keep `MCP_DATA_BASE_DIR` and `MCP_LOGS_DIR` on persistent paths outside the Node working directory.
- `useLean=true` on `ws_load` / `ws_get_records` cuts tokens 40–60% on large result sets.
- OAuth secrets are hashed and unrecoverable — if lost, delete and recreate the client.
