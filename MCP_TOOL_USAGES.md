# Maximo MCP -- Agent Operating Guide

This guide is for an AI agent that has the Maximo MCP tools. The tool schemas already list every
parameter. This guide covers what the schemas cannot: WHICH tool fits an intent, in WHAT ORDER to
call tools, how to READ what comes back, where you MUST stop for the user, and the rules that
prevent the failures that have actually happened.

Read sections 0-3 once; they apply to every task. Use section 4 as recipes, section 5 as the query
reference, section 6 as the rule list.

---

## 0. Know what you have

Your tool list is the truth. If a tool is not in your list, it does not exist on this server --
do not try to reach the same effect through another tool.

| Deployment               | What you have                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Full (premium)           | Everything in this guide, plus configuration tools (Configure Database, Admin Mode, system properties, read-only SQL, cache reload, App Designer editing, `ws_commit_status`)                                                                                                                                                                                                                    |
| Public                   | Everything in this guide except those configuration tools                                                                                                                                                                                                                                                                                                                                        |
| Read-only (`--readonly`) | Only: `maximo_get_metadata`, `os_query_builder` (query only), `ws_load`, `ws_next_page`, `ws_previous_page`, `ws_get_records`, `ws_get_allowed_actions`, `ws_list_attachments`, `ws_get_attachment`, `maximo_get_allowed_actions`, `maximo_get_url`, plus `mcp_server_status` and `mcp_read_logs`. If the operator enabled script-get, also `maximo_invoke_automation_script` in a GET-only form |

If the user asks for a change and you only have read tools, say so plainly. Do not improvise a
write.

---

## 1. Golden rules

1. Look before you act. Discover names with `maximo_get_metadata`; never guess an object
   structure or field name.
2. Nothing changes data without a preview and the user's yes. Working set: `ws_preview_changes`
   then `ws_commit`. Status: `maximo_plan_status_change` then `maximo_change_status`. Import:
   preview first. Show the user what will happen, then wait.
3. Success means `op_success: true`. Anything else is a failure, however the data looks.
4. Quote Maximo's own error text and `BMXAA` codes. Do not paraphrase them away.
5. Quote `meta.totalCount` for "how many", never the page length.
6. Use the dedicated tool. `maximo_get_url` and `maximo_invoke_automation_script` are last
   resorts, never a way around a confirmation step.
7. A tool you were refused (`permission_denied`, `*_not_allowed`) is a stop sign, not a puzzle.
   Report it; do not search for a side door.

---

## 2. Pick the tool

| The user wants to...                         | Use                                                                                             |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| find or list records                         | `maximo_get_metadata` -> `os_query_builder` -> `ws_load`                                        |
| know how many records match                  | `os_query_builder` with `count:true` -> `ws_load` -> `meta.totalCount`                          |
| see the next / previous page                 | `ws_next_page` / `ws_previous_page`                                                             |
| see related rows (children, other objects)   | `os_query_builder` (`select` child block, `rel.` path, `childOptions`, `childCollection`)       |
| create a record                              | `ws_init_new_record` -> `ws_update_draft` -> `ws_preview_changes` -> `ws_commit`                |
| change fields on existing records            | `ws_set_active` -> `ws_update_field` / `ws_multi_update` -> `ws_preview_changes` -> `ws_commit` |
| add or remove one child row                  | `ws_add_child_record` / `ws_remove_child_record`                                                |
| delete a record                              | `ws_delete_record` -> `ws_preview_changes` -> `ws_commit`                                       |
| change a status (WAPPR -> APPR ...)          | `maximo_plan_status_change` -> user confirms -> `maximo_change_status`                          |
| approve / reject a workflow task             | `maximo_get_workflow_assignments` -> `maximo_send_workflow_response`                            |
| know what can be done to a record            | `maximo_get_allowed_actions` (one) / `ws_get_allowed_actions` (every loaded row at once)        |
| run an action that is not status or workflow | `maximo_invoke_action`                                                                          |
| load a CSV / XML file                        | `maximo_import_file` (preview) -> user confirms -> `maximo_import_file` (`preview:false`)       |
| list / download attachments                  | `ws_list_attachments` -> `ws_get_attachment`                                                    |
| run an automation script                     | `maximo_invoke_automation_script` (only a script the user named or approved)                    |
| read an endpoint no tool covers              | `maximo_get_url` (GET only)                                                                     |
| see what was changed through this server     | `maximo_get_audit_logs`                                                                         |
| keep values between steps                    | `ctx_create` / `ctx_set` / `ctx_get`                                                            |
| check the server or the first sync           | `mcp_server_status`, `mcp_read_logs` (diagnostics)                                              |

---

## 3. How tools answer

### 3.1 The envelope

Results are JSON text. Most tools return `op_success`:

- success: `op_success: true`, plus the data
- failure: `op_success: false` and `error: { reason, detail }`. `reason` is a stable code you can
  branch on; `detail` is for humans (and often carries Maximo's own message).

`os_query_builder` (and sometimes `maximo_get_metadata`) return data without `op_success`; treat an
`error` key there as a failure.

HTTP 204 "No content" from an action or status call is success: nothing to read back.

### 3.2 Where you must stop for the user

| Step                                      | Stop and ask when                                                                                                                                                                                              |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ws_commit`                               | Always, after `ws_preview_changes`. For destructive work pass `requireConfirmation:true`: it returns `needs_confirmation` with the staged changes; call again with `confirmed:true` only after the user agrees |
| `maximo_change_status`                    | After `maximo_plan_status_change` has been shown                                                                                                                                                               |
| `maximo_import_file` with `preview:false` | After the preview counts and warnings were shown                                                                                                                                                               |
| `maximo_invoke_action`                    | Before running, unless the user already asked for exactly that action                                                                                                                                          |
| `maximo_send_workflow_response`           | Omit `actionName` first to list allowed actions; run only the one the user picks                                                                                                                               |
| `maximo_invoke_automation_script`         | Always: scripts run immediately with no preview                                                                                                                                                                |
| electronic signature                      | When asked for a credential or reason (see 4.9)                                                                                                                                                                |

### 3.3 Error playbook

| `error.reason` (or code)                                                                                            | What it means                                             | Do this                                                                      |
| ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `metadata_sync_in_progress`                                                                                         | First metadata sync still running                         | Wait and retry; `mcp_server_status` shows progress. Do not report a failure  |
| `ws_not_found`                                                                                                      | The working set expired                                   | Rebuild with `os_query_builder` and continue; no need to tell the user       |
| `permission_denied`                                                                                                 | The API user lacks rights                                 | Report it; do not retry or route around it                                   |
| `no_active_record`                                                                                                  | `restID:"active"` used with nothing active                | `ws_set_active` first                                                        |
| `needs_confirmation`                                                                                                | `ws_commit` was asked to confirm                          | Show the staged changes; recommit with `confirmed:true` after yes            |
| `validation_errors` / `invalid_domain_value` at commit                                                              | A field value was rejected                                | Read each `attribute` + `detail`; fix; build a fresh working set (rule R10)  |
| `no_next_page` / `no_previous_page`                                                                                 | Maximo returned no such link                              | You are at the end; tell the user                                            |
| `unstaged_changes_block_paging`                                                                                     | Staged changes exist                                      | `ws_commit` or `ws_discard`, then page                                       |
| `status_change_not_allowed`                                                                                         | The action is not currently allowed                       | Show `allowed_actions`; ask the user                                         |
| `esig_required`                                                                                                     | An electronic signature is required and none is available | Ask for their e-signature key and a reason (4.9)                             |
| `esig_invalid_server_credential`                                                                                    | The server's own configured signature was rejected        | An operator problem: report it; do NOT ask the user for a password           |
| `action_not_allowed`                                                                                                | `maximo_invoke_action` name not allowed on this record    | `maximo_get_allowed_actions` and pick again                                  |
| `import_file_failed`                                                                                                | Maximo rejected the import                                | Show `detail` and `maximo_error` verbatim (e.g. an unknown object structure) |
| `host_not_allowed`, `path_not_allowed`, `header_not_allowed`, `action_param_not_allowed`, `script_path_not_allowed` | `maximo_get_url` guard refused the request                | Do not retry the same thing; use the tool named in `detail`                  |
| `status_url_not_allowed`                                                                                            | `maximo_import_file_status` got a foreign URL             | Pass `statusUrl` exactly as `maximo_import_file` returned it                 |
| `BMXAA...`                                                                                                          | Maximo's own business rule                                | Quote it; fix the data if the message says how                               |

### 3.4 State: working sets and ctx

- `os_query_builder` builds the query AND creates a working set; its id comes back in the
  `workingSet` field. `ws_init_new_record` returns its own `wsId`. Every `ws_*` call needs that id.
- A working set holds loaded records and staged changes in memory. It expires after inactivity
  (sliding timeout). On `ws_not_found`, rebuild it.
- `ws_discard` drops staged changes and keeps the loaded records. `ws_remove` deletes the whole
  working set. Remove sets you are finished with.
- While a commit runs the set is locked. Never re-commit after a timeout; see R16.
- `ctx_*` is a small key-value store for the conversation (for example `resolved.osName`). It
  never touches Maximo. It is not available in read-only mode.

---

## 4. Recipes

`restId` and `restID` always mean the record's REST id: the last path segment of its `href`
(for example `_QkVERk9SRC81MDA4`). Take it from a query result; never build it yourself.

### 4.1 Read records

1. `maximo_get_metadata` `maximo://os/search/{keyword}` to find the object structure, then
   `.../schema` for field names. Skip only if you already confirmed them in this session.
2. `os_query_builder` (`opAction:"query"`, `osName`, `select`, `where`, `pageSize`).
3. `ws_load` with `useLean:true`. Decode the lean payload (section 5.6) before presenting.
4. Present rows. If `meta.totalCount` exceeds the rows shown, say so.

### 4.2 Count only

`os_query_builder` with `count:true` (same `where`), then `ws_load`. Read `meta.totalCount`;
`result` is empty by design and `hasMore` is not set. This is the cheapest "how many". Use
`collectioncount:true` instead when you also want the rows.

### 4.3 Page through results

1. Query with `pageSize` and `collectioncount:true`, then `ws_load`.
2. `meta.paging` gives `pagenum`, `totalPages`, `nextPage`, `previousPage`.
3. `ws_next_page` / `ws_previous_page`. Each replaces the loaded records. They refuse while there
   are staged changes and when Maximo returned no such link.
4. To jump to a page directly, set `pageno` (1-based) on the query instead.

### 4.4 Create a record

1. `ws_init_new_record` (`osName`). Returns `wsId`, `draftRecord` (with `_tempId`) and per-field
   `metadata` (readOnly / required / constrained values).
2. Read `metadata` first. Do not send readOnly fields. Do not re-send fields the draft already
   filled (`wonum` / `ticketid`, `class`, `reportdate`, `historyflag`).
3. `ws_update_draft` (`id`, `temp_id` = the draft's `_tempId`, `record` = only the fields you set).
   Child arrays are allowed, for example `{ workorderspec: [ { assetattrid:"X", alnvalue:"Y" } ] }`.
   Do not put `_tempId` inside `record`.
4. Domain-constrained fields: use a value that exists in the domain; if unsure, omit the field.
5. `ws_preview_changes` -> show the user -> yes -> `ws_commit`.
6. On success the status is 201 and the location holds the new record. On failure see
   `validation_errors` in 3.3; never reuse the working set (R10) and stop after two failed
   attempts, reporting the fields and reasons.

### 4.5 Update existing records

1. `os_query_builder` + `ws_load` the records.
2. `ws_set_active` with `restID:"0"` (a 0-based index is simplest), then `ws_get_active` to
   confirm it is the right record. Or pass `restID:"active"` / the record's restId directly.
3. Stage: `ws_update_field` (one field), `ws_multi_update` (`updates:[{restID, fields:{...}}]`,
   several fields or records), or `ws_batch_update` (`spec:{filter, field, value}` for one value
   across many rows). Prefer the deterministic forms; `spec.updater` is free text.
4. `ws_preview_changes` -> before/after to the user -> yes -> `ws_commit`.
5. Never stage a status through `ws_update_field` (R14). Never stage readOnly fields.

### 4.6 Child rows and deletes

- One child row: `ws_add_child_record` (`field` = the relationship array name from
  `relatedObjects`, `record` = the row) or `ws_remove_child_record` (`keyValues` OR `index`).
- Delete a record: `ws_delete_record`, then preview, then commit with `requireConfirmation:true`.

### 4.7 Related data in a query

Pick by what you need (details and names in 5.3):

- all child rows of the object structure's own children: a child block in `select`
- a relationship the object structure does not expose: `rel.<name>{...}` in `select`
- only some child rows, across all parents: `childOptions` (relationship must also be selected)
- child rows of one parent, paged or counted: `childCollection`

### 4.8 Status change

1. Find the record (4.1) and note its restId.
2. `maximo_plan_status_change` (`osName`, `restId`, `newStatus`, optional `memo`). It changes
   nothing. Show the user: current status, requested status, whether it is allowed, and the
   allowed actions.
3. Only after a yes: `maximo_change_status` with the same values. Optional `memo` (50 characters
   at most -- Maximo rejects more), optional `statusDate` (ISO 8601; defaults to now in UTC).
4. The status action name is found for you (it differs by object structure, for example
   `changeWOStatus`). Pass `actionName` only to override; `changeStatus` is accepted as the global
   action. Single record only.
5. Success is a 204. Optionally reload and confirm the new status.

### 4.9 Electronic signature on a status change

Maximo can require an electronic signature (a SIGOPTION setting) for an action.
`maximo_change_status` always asks Maximo to enforce it.

- If the server operator configured a service-account signature, it is applied for you and the
  call just works. Ask the user only for a reason and pass it as `esigReason` (optional).
- If you get `esig_required`: ask the user for their Electronic Signature key (their Maximo
  password) and a reason. Call `maximo_change_status` again with the same values plus
  `esigAuth` = base64 of the PASSWORD ONLY (not `user:password`) and `esigReason`.
- `esig_invalid_server_credential` is an operator problem. Report it. Never ask the user for a
  password to fix it.
- A wrong user-supplied `esigAuth` comes back as Maximo's `BMXAA3840E`: ask them to re-enter it.

### 4.10 Workflow tasks

1. `maximo_get_workflow_assignments` (`includeAllowedActions:true` returns action names in one
   call; it costs one extra request per assignment, so keep `pageSize` small).
2. Show the tasks; ask which to action and how.
3. `maximo_send_workflow_response`: `osName` = the OWNING record's object structure (for example
   `MXAPIWO`), NOT the assignment's; `restId` = the assignment's `ownerid`, NOT its own id. Omit
   `actionName` to list what is allowed; call again with `actionName` to execute.

### 4.11 Actions on records

1. One record: `maximo_get_allowed_actions`. Many rows: `ws_get_allowed_actions` returns every
   loaded row's actions in one call (it re-runs the working set's own query).
2. Each action lists its `httpmethod`, a `description`, and what to send: `requestSchema` (the
   body, for POST) or `requestQueryParams` (for GET). `type` is `wsmethod` or `system`.
3. `maximo_invoke_action` with the `actionName` exactly as listed and `params` shaped by that
   schema. It re-checks that the action is still allowed and uses the right HTTP method for you.
4. For status changes and workflow responses use their own tools; they add the confirmation step.

### 4.12 Import a file

1. Build the document: CSV with a header row of attribute names (`fileType:"FLAT"`, the default) or
   XML (`fileType:"XML"`). CSV needs the object structure to have "Support Flat Structure" on.
2. `maximo_import_file` (default `preview:true`). Nothing is written. Show `totaldoc`, `validdoc`,
   `invaliddoc`, `warningmsg`.
3. If the user accepts: call again with the same `content` and `preview:false`.
4. Large file: add `async:true` (and a unique `name`). You get a `statusUrl`; poll
   `maximo_import_file_status` until `iscomplete` is true. Pass `statusUrl` unchanged.

### 4.13 Attachments

`ws_list_attachments` (`id`, `restID`), then `ws_get_attachment` with `attachmentRef` = the
attachment's `describedBy.identifier` or its `href`.

### 4.14 Automation scripts

Only run a script the user named or approved. `maximo_invoke_automation_script` runs it at once
with no preview, and a script can change data even on GET.

- `scriptName`, optional `params` (query string).
- Full deployments also take `httpMethod:"POST"` and a JSON `body` (the script reads it as
  `request`). A read-only server with script-get enabled accepts GET only.
- `op_success` is true on a 2xx; `httpStatus` and `body` carry the script's answer. Some scripts
  return very large bodies; narrow them with `params` where the script allows.

### 4.15 Anything else that is a read: `maximo_get_url`

Use it only when no dedicated tool fits, for example `/oslc/whoami`, a child collection `href`,
or `/api/error/messages/<code>`.

- `url` is a path on this Maximo (`/api/os/mxapiwo?oslc.pageSize=5`) or a full URL on the same
  host. Add `params` and `headers` if needed; `maxBytes` caps the body (default 200000).
- GET only, same host only, no redirects followed, credential headers refused. JSON comes back
  parsed; large bodies are truncated and binary bodies omitted (use `ws_get_attachment`).
- It refuses `action=` parameters and `/api/script` paths because those can change data. Use
  `maximo_invoke_action` / `maximo_invoke_automation_script`. Do not try to disguise them.
- For record queries prefer `os_query_builder` + `ws_load`; they validate and feed the working set.

### 4.16 Audit and diagnostics

`maximo_get_audit_logs` (filters: `fromTs`, `toTs`, `wsId`, `osName`, `operation`) lists working
set create/update/delete/commit events; it needs `AUDIT_ENABLED=true` on the server.
`mcp_server_status` reports version, sync progress and configuration; `mcp_read_logs` tails logs.

---

## 5. Query reference (`os_query_builder`)

`opAction` is `"query"`. `osName` is required. `lean` defaults to true; leave it.

### 5.1 where

Conditions are ANDed; set `orMode:true` for OR.

    { "conditions": [ { "field": "siteid", "op": "=", "value": "BEDFORD" },
                      { "field": "status", "op": "in", "value": ["WAPPR","APPR"] } ] }

- ops: `=`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `like` (value `"%pump%"`), `isnull`, `isnotnull`
  (no value needed; they render as `attr!=_` and `attr=_`)
- dates: ISO 8601, for example `"2025-01-01T00:00:00+00:00"`
- dot notation filters PARENTS by a child attribute and uses the OBJECT name as prefix:
  `{ "field": "ASSETSPEC.NUMVALUE", "op": ">", "value": 300 }`
- `rawWhere` is a raw OSLC string for mixed AND/OR nesting. It silently OVERRIDES the structured
  `where`; never set both.
- Parenthesised and/or nesting inside a structured where is not supported.

Extra filters: `searchTerms` (+ `searchAttributes`) full-text search; `savedQuery` (+
`savedQueryParams`); `domaininternalwhere` filters by a synonym-domain attribute's INTERNAL
values (`status=APPR,INPRG`, `!=` excludes) instead of the display value; `tlrange` +
`tlattribute` timeline filter around an index date (`-3M` last three months, `+-3Y` both ways).

### 5.2 select

`select: { "fields": [ ... ] }` where each entry is one of:

- a plain attribute: `"wonum"`
- an alias: `{ "alias": { "attr": "asset.description", "as": "assetdesc" } }`
- a child block: `{ "child": "worklog", "attrs": ["description","createdate"] }`
- a relationship path string: `"rel.asset{assetnum,rel.assetmeter{metername,lastreading}}"`

`rawSelect` is a raw string that overrides `select`.

### 5.3 Related data: three ways, three different names

A wrong token returns EMPTY rows, never an error, so choose deliberately.

1.  Child the object structure already exposes -> a child block keyed by the child OBJECT name,
    lowercased: `{ "child": "worklog", ... }`, NOT the relation name `woworklog`. Returns ALL child
    rows; it cannot filter them. Get names from `maximo://os/{osName}/relatedObjects`
    (`objectName`, `relation`, `cardinality`).
2.  Any relationship, including ones the object structure does not expose -> `rel.<relationshipName>{...}`
    (the RELATIONSHIP name). Nests two levels. Names come from
    `maximo://object/{primaryObject}/relationships/compact`.
3.  Only some child rows, sorted or paged -> `childCollection`, which queries one parent's child
    collection as its own collection. It is the ONLY way to page or `collectioncount` child rows;
    `select` / `where` / `orderBy` / `pageSize` then apply to the CHILD rows.

         "childCollection": { "parentRecordId": "<restId or href>", "relationship": "woactivity", "responseOs": "MXAPIASSET" }

    `responseOs` re-renders the far side through that object structure and is REQUIRED to reach the
    far side's own children.

Every related result is a LIST of 0..N rows. A 1:1 relationship still arrives as a one-element
array, and a missing child key means zero rows, not a bad query.

### 5.4 childOptions (filter and sort child rows across all parents)

`childOptions` `where` / `orderBy` / `limit` act on child rows you already selected. Two things
must both be true or it does nothing:

1. the relationship is ALSO selected (child block or `rel.<name>{...}`);
2. for anything nested past one relationship hop, `path` is set to the full relationship-name chain
   from the primary object down to the filtered relationship (for example
   `["MODIFYWORKLOG","PERSON","SMS"]`).

If the response carries a `warnings` array naming a childOptions entry, read it: it says which of
the two was not satisfied. For ONE parent, or to page child rows, use `childCollection`.

### 5.5 Everything else

- `orderBy`: `{ "rules": ["-wopriority","+wonum"] }`. The direction prefix is mandatory.
- `pageSize` (default 20), `pageno` (1-based), `paging:true` (oslc.paging).
- `collectioncount:true`: total in `meta.totalCount` plus the rows. Also works on a
  `childCollection` query (a per-parent child total).
- `count:true`: Maximo runs `SELECT COUNT(*)` and returns only the total, no rows (4.2).
- `ignorecollectionref:true`: drops the `*_collectionref` child hrefs from every record.
- `addschema:true`: Maximo inlines the JSON schema for this exact query; `ws_load` returns it in
  `meta.schema`. A next-page link does not carry it, so set it again on a later page's own query.
- `relativeuri:true` shorter hrefs (recommended); `internalvalues:true` internal codes;
  `basePath` only for legacy OSLC (default `/api/os`).

NOT supported -- do not attempt: aggregation (`_dbcount`, `_dbsum`, `_dbavg`, `_dbmax`, `_dbmin`
on a related set are accepted and silently dropped; there is no GROUP BY; `count` /
`collectioncount` are the only counts) and and/or nesting inside `oslc.where`.

### 5.6 Reading `ws_load` (and `ws_get_records`, `ws_next_page`, `ws_previous_page`)

Always set `useLean:true`. A lean payload carries `### SCHEMA` (short key -> full field name) and
`### DICT` (`*N` pointer -> repeated string). Decode BOTH before presenting data. Hrefs and ISO
dates are never encoded.

`meta` fields: `count` (rows in this page), `totalCount` (matching rows in Maximo -- needs
`collectioncount` or `count`), `hasMore` (more pages remain), `paging` (`pagenum`, `totalPages`,
`nextPage`, `previousPage`), `schema` (with `addschema`). Quote `totalCount`, never `count`.

---

## 6. Critical rules

R1. `childOptions` only works if the relationship is ALSO selected and, past one hop, `path` is
set. Read the `warnings` array rather than assuming empty means nothing matched.

R2. Dot notation in `where` uses the objectName prefix, never the relation name.
Wrong `labtrans.TRANSTYPE`; right `LABTRANS.TRANSTYPE`.

R2b. A child `select` block key is the objectName lowercased, never the relation name.
Wrong `woworklog`; right `worklog`. The wrong one returns nothing and no error.

R2c. `rel.<name>{...}` takes the RELATIONSHIP name from `relationships/compact`.
`rel.asset{assetnum}` works even when ASSET is not in `relatedObjects`.

R3. `orderBy` needs a direction prefix: `["-wopriority"]`, not `["wopriority"]`.

R4. `rawWhere` silently overrides the structured `where`. Never set both.

R5. Nothing in a parent query filters child rows. Dot notation and brace notation both filter
PARENTS and the child block still comes back whole. Filter child rows with `childOptions`
(or `childCollection` for one parent).

R6. Working set ids expire. On `ws_not_found`, silently rebuild with `os_query_builder` and
continue.

R7. `maximo_send_workflow_response` targets the OWNING record: its `osName`, and the assignment's
`ownerid` as `restId`. Not the assignment's own id.

R8. Prefer `maximo://os/...` URIs. The only `maximo://object/...` URI you may use is
`.../relationships/compact`, to name a relationship `relatedObjects` omits. Any other
`maximo://object/...` bypasses object-structure security.

R9. Never send readOnly fields in `ws_update_draft`, `ws_update_field` or `ws_multi_update`.

R10. Never reuse a working set after a failed commit. Build a fresh one (`ws_init_new_record` for
a create).

R11. In `ws_update_draft`, pass the draft's `_tempId` as `temp_id`, not inside `record`.

R12. For domain-constrained fields, omit rather than guess. A wrong value fails at commit with
`invalid_domain_value`.

R13. Never `ws_commit` without `ws_preview_changes` and the user's confirmation first.

R14. Never change a status with `ws_update_field`. Use `maximo_plan_status_change` then
`maximo_change_status`.

R15. If `ws_commit` returns `{ async: true, asyncId }` the commit is NOT finished. Poll
`ws_commit_status` (about every 30 s) until it reports `succeeded` or `failed`, and report success
only on a terminal status. Full deployments only: the public edition has no `ws_commit_status` and
never returns `asyncId`; there, `ws_commit` completes before it responds and its result is final.

R16. Never re-commit after a `ws_commit` timeout. The working set stays locked while the commit
runs and a retry is refused. If you lost the `asyncId`, call `ws_commit_status` with the working
set id.

R17. Trust the `warnings` array over your own assumption. It reports things Maximo accepted but
did not honour, which otherwise look like correct empty results.

R18. Do not use `maximo_get_url`, `maximo_invoke_automation_script` or a hand-built URL to bypass
a gate. Changing data goes through the working set (preview + commit) or the status / action tools
with their confirmation steps.

R19. `esigAuth` is base64 of the PASSWORD ONLY, never `user:password`. If the server has its own
signature configured, never ask the user for a password; if that signature is rejected, report it
to an operator.

R20. A `status` memo is limited to 50 characters. Keep it short or Maximo rejects the change.

R21. Do not wrap a tool call in a loop to "make sure" it worked. Re-read the record with
`os_query_builder` + `ws_load` if you need to verify a change.
