# Maximo MCP Tools - Usage Guidelines

These rules are the source of truth for agent orchestration in this repo.
See `AGENT_CONTEXT_PATTERN.md` for the Context Envelope v1 contract.

---

## 1) Operation Pipelines

All pipelines below run inside the respective core agent. Process agents delegate to core agents
and never call these tools directly.

### READ
```
os_query_builder -> ws_load(useLean=true) -> ws_get_records(useLean=true) -> decode LEAN -> return
```

### CREATE
```
ws_init_new_record -> ws_update_draft(id, temp_id, record) -> ws_preview_changes -> [user confirm] -> ws_commit
```

### UPDATE
```
os_query_builder -> ws_load -> ws_set_active(restID='0') -> ws_multi_update(restID='active')
-> ws_preview_changes -> [user confirm] -> ws_commit
```

### STATUS CHANGE
```
os_query_builder -> ws_load(useLean=false) -> ws_get_records(useLean=false)
-> extract restId from href (last path segment)
-> maximo_plan_status_change -> [user confirm] -> maximo_change_status
```

### WORKFLOW
```
maximo_get_workflow_assignments(includeAllowedActions=true)
-> [user picks action] -> maximo_send_workflow_response
```

---

## 2) maximo_get_metadata

Used only by `maximo_metadata_agent`. URI patterns:
- `maximo://os/search/{keyword}` - resolve_os
- `maximo://os/{osName}/schema` - get_schema
- `maximo://os/{osName}/relatedObjects` - get_related_objects
- `maximo://os/{osName}/subschemas/{childObjectName}` - get_subschema
- `maximo://os/{osName}/object/{objectName}/attributes/{attributeNameOrCsv}` - get_attribute_metadata

Rules:
- Always set `useLean: true`.
- Decode LEAN `DICT` + `SCHEMA` before returning - never return raw LEAN text.
- Domain values are only returned for `SYNONYM`, `ALN`, `NUMERIC` domain types.
  `CROSSOVER` and `TABLE` domains are skipped (unbounded reference sets).

---

## 3) os_query_builder

Creates a working set. Returns a `wsId` that must be passed to `ws_load`.

Required fields:
- `osName` - full OS name (e.g. `MXAPISR`, not `SR`)
- `opAction: "query"`

### rawWhere (preferred)
Build directly from `identifierField` + `identifierValue`:
```
ticketid="1002"
ticketid="1002" and siteid="BEDFORD"
wonum="WO-500" and siteid="BEDFORD"
status in ["QUEUED","INPROG"] and siteid="BEDFORD"
```

CRITICAL: the "in" operator uses SQUARE brackets, never round brackets.
- Correct:  status in ["QUEUED","INPROG"]
- Wrong:    status in ("QUEUED","INPROG")

### select
Flat string array:
- All fields: `["*"]`
- Specific: `["wonum", "status", "description"]`

### childSelects
Object map, key is relationship name:
```json
{ "assignment": ["laborcode", "scheduledate"], "worklog": ["*"] }
```

### orderBy
Direction required: `+field`, `-field`, `field asc`, `field desc`. Never bare `field`.

---

## 4) Working Set tools

### ws_load
Loads records into an existing working set created by `os_query_builder` or `ws_init_new_record`.
Signature: `ws_load(id=<wsId>, useLean=true|false)`.
**Never call `ws_load` without a valid `wsId` from a prior `os_query_builder` call.**

### ws_get_records
Returns records from a loaded working set.
- Use `useLean=true` for read operations.
- Use `useLean=false` when restId extraction from `href` is needed (status/workflow).
- Decode LEAN `### SCHEMA` and `### DICT` before using field values.

### restId extraction
For status and workflow, extract `restId` as the last path segment of `href`:
```
href: /api/os/MXAPISR/1234  ->  restId: "1234"
```

### ws_set_active
Activates a record in the working set for field updates.
Always call with `restID='0'` to activate the first (and only) record.

### ws_multi_update
Stages field changes on the active record.
```json
{ "restID": "active", "stringFields": { "description": "new value" }, "numericFields": { "reportedpriority": 2 } }
```
String values -> `stringFields`. Numeric values -> `numericFields`. Never mix types.

### ws_init_new_record
Starts a new record working set for create flows. Returns `wsId` and `draftRecord._tempId`.
Both must be stored in ctx (`draft.wsId`, `draft._tempId`) immediately after this call.

### ws_update_draft
Populates the draft record created by ws_init_new_record. Required params: id (wsId), temp_id (_tempId from init), record (field map).
Do NOT include _tempId inside the record object - pass it as the top-level temp_id parameter.
Pass all caller-supplied fields as-is. Exclude: _id, href, _rowstamp, changeby, changedate.
Child arrays (e.g. invuseline) are fully supported in the record object.

### ws_preview_changes
Validates staged changes against Maximo before commit. Must be called before `ws_commit`.
If preview returns explicit errors: call `ws_remove`, return error. Do not commit.

### ws_commit
Commits the staged working set to Maximo. Only call after `ws_preview_changes` succeeds
and user has confirmed. On failure: return the error payload unchanged.

### ws_remove
Cleans up a working set. Call on error paths to avoid orphaned working sets.

---

## 5) Status tools

### maximo_plan_status_change
- Requires `osName`, `restId` (numeric, from href), and optionally `newStatus`.
- Returns current status and allowed transitions.
- Always call before `maximo_change_status`.

### maximo_change_status
- Call only after plan and explicit user confirmation.
- Requires `osName`, `restId`, `newStatus`. Optional: `memo`, `statusDate`.

---

## 6) Workflow tools

### maximo_get_workflow_assignments
- Always pass `includeAllowedActions: true`.
- Returns assignments with `ownerid`, `processName`, `taskDescription`, `allowedActions`.
- `ownerid` is the value to pass as `restId` to `maximo_send_workflow_response`.

### maximo_send_workflow_response
- `restId` = `ownerid` from the assignment (not the assignment id itself).
- `osName` must be the owning record's OS (e.g. `MXAPISR`).
- `actionName` must be an exact string from the `allowedActions` list - never guessed.

---

## 7) Non-negotiables
- No fabricated data on any tool or agent failure.
- `ws_load` requires a valid `wsId` - never call it without one.
- Always call `ws_preview_changes` before `ws_commit`.
- Require explicit user confirmation before any write (commit / execute / change_status / send_workflow_response).
- Domain values are not validated by agents for CROSSOVER/TABLE domain types - Maximo validates at commit.
- Process agents never call MCP tools other than ctx_*.
