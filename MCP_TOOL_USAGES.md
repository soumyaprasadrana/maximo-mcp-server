# Maximo MCP -- Agent Operating Guide

Applies to maximo-mcp-server 2.1.0.

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
| Default | Every tool in this guide except the ten configuration tools, `mcp_read_logs` (dev mode) and the opt-in `maximo_read_server_log`; includes `ws_commit_status` and `mcp_server_status` |
| `--copilot-mode` | Adds the ten configuration tools (4.18): `maximo_copilot_setup`, `maximo_dbconfig_status`, `maximo_dbconfig_apply_status`, `maximo_dbconfig_discard`, `maximo_dbconfig_apply`, `maximo_admin_mode`, `maximo_sql_query`, `maximo_system_property`, `maximo_reload_cache`, `maximo_appdesigner_edit` |
| Read-only (`--readonly`) | Only reads: `maximo_get_metadata`, `os_query_builder` (query only), `ws_load`, `ws_next_page`, `ws_previous_page`, `ws_get_records`, `ws_remove`, `ws_get_allowed_actions`, `ws_list_attachments`, `ws_get_attachment`, `maximo_get_allowed_actions`, `maximo_get_url`, `maximo_get_workflow_assignments`, `maximo_lookup_values`, `maximo_aggregate`, `maximo_list_reports`, `maximo_run_report`, `maximo_integration_errors`, plus `mcp_server_status` and `mcp_read_logs`. If the operator enabled script-get, also `maximo_invoke_automation_script` in a GET-only form |
| Opt-in (any mode) | `maximo_read_server_log` only when the operator set `MCP_ENABLE_SERVER_LOGS` |
| Per-user identity (`--caller-apikey`) | You act as the Maximo user whose API key the request carries; working sets are private to that user. `mcp_read_logs`, `ctx_list` and `maximo_read_server_log` are withheld |

Strict-schema servers (`--strict-tool-schema`, used by watsonx Orchestrate and Copilot Studio)
take different shapes for a few parameters -- see 5.7. Always follow the schema in your tool list.

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
| approve / reject a workflow task             | `maximo_get_workflow_assignments` -> `maximo_complete_workflow_assignment` (plan, then confirm) |
| start a workflow on a record                 | `maximo_start_workflow` (plan, then confirm)                                                    |
| know valid values for a field                | `maximo_lookup_values` (also table fields: asset, location, work type, crew ...)                |
| count / sum / average per group              | `maximo_aggregate` -- never load records to count them                                          |
| run a report (PDF)                           | `maximo_list_reports` -> `maximo_run_report`                                                    |
| attach a file to a record                    | `ws_add_attachment` (plan, then confirm)                                                        |
| check integration (MIF) failures             | `maximo_integration_errors`                                                                     |
| see Maximo's own errors / server log         | `maximo_read_server_log` (only if the operator enabled it)                                      |
| know what can be done to a record            | `maximo_get_allowed_actions` (one) / `ws_get_allowed_actions` (every loaded row at once)        |
| run an action that is not status or workflow | `maximo_invoke_action`                                                                          |
| load a CSV / XML file                        | `maximo_import_file` (preview) -> user confirms -> `maximo_import_file` (`preview:false`)       |
| list / download attachments                  | `ws_list_attachments` -> `ws_get_attachment`                                                    |
| run an automation script                     | `maximo_invoke_automation_script` (only a script the user named or approved)                    |
| read an endpoint no tool covers              | `maximo_get_url` (GET only)                                                                     |
| see what was changed through this server     | `maximo_get_audit_logs`                                                                         |
| keep values between steps                    | `ctx_create` / `ctx_set` / `ctx_get` (`ctx_remove` a key, `ctx_delete` the context)             |
| check this MCP server or the first sync      | `mcp_server_status` (always), `mcp_read_logs` (dev mode / read-only)                           |

---

## 3. How tools answer

### 3.1 The envelope

Results are JSON text. Most tools return `op_success`:

- success: `op_success: true`, plus the data
- failure: `op_success: false` and `error: { reason, detail }`. `reason` is a stable code you can
  branch on; `detail` is for humans (and often carries Maximo's own message).

`os_query_builder` (and sometimes `maximo_get_metadata`) return data without `op_success`; treat an
`error` key there as a failure, and treat an `os_query_builder` answer with no `workingSet` id as a
failure too.

HTTP 204 "No content" from an action or status call is success: nothing to read back.

### 3.2 Where you must stop for the user

| Step                                      | Stop and ask when                                                                                                                                                                                              |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ws_commit`                               | Always, after `ws_preview_changes`. For destructive work pass `requireConfirmation:true`: it returns `needs_confirmation` with the staged changes; call again with `confirmed:true` only after the user agrees |
| `maximo_change_status`                    | After `maximo_plan_status_change` has been shown                                                                                                                                                               |
| `maximo_import_file` with `preview:false` | After the preview counts and warnings were shown                                                                                                                                                               |
| `maximo_invoke_action`                    | Before running, unless the user already asked for exactly that action                                                                                                                                          |
| `maximo_complete_workflow_assignment`     | Always: call without `confirm` first, show the task, owner and route, then `confirm:true` after a yes                                                                                                         |
| `maximo_start_workflow`                   | Always: call without `confirm` first, then `confirm:true` after a yes                                                                                                                                          |
| `ws_add_attachment`                       | Always: not staged -- call without `confirm` first, then `confirm:true` after a yes                                                                                                                            |
| `maximo_send_workflow_response`           | Omit `actionName` first to list allowed actions; run only the one the user picks                                                                                                                               |
| `maximo_invoke_automation_script`         | Always: scripts run immediately with no preview                                                                                                                                                                |
| configuration tools (copilot mode)        | Always before `confirm:true`: `maximo_dbconfig_apply` (also `confirmToken:"APPLY"`), `maximo_dbconfig_discard`, `maximo_admin_mode`, `maximo_sql_query`, `maximo_system_property` `set`, `maximo_appdesigner_edit` `commit` (see 4.18) |
| electronic signature                      | When asked for a credential or reason (see 4.9)                                                                                                                                                                |

### 3.3 Error playbook

| `error.reason` (or code)                                                                                            | What it means                                             | Do this                                                                      |
| ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `metadata_sync_in_progress`                                                                                         | First metadata sync still running                         | Wait and retry; `mcp_server_status` shows progress. Do not report a failure  |
| `metadata_fetch_failed` | On-demand metadata could not be fetched from Maximo and none is cached | Report it; retry later. The first call on an object structure can take a few seconds -- that is normal |
| `ws_not_found` / `workingset_not_found`                                                                             | The working set expired, or (per-user servers) belongs to another user | Rebuild with `os_query_builder`. If it held staged, uncommitted changes, tell the user they were lost, re-stage and preview again |
| `permission_denied`                                                                                                 | The API user lacks rights                                 | Report it; do not retry or route around it                                   |
| `no_active_record`                                                                                                  | `restID:"active"` used with nothing active                | `ws_set_active` first                                                        |
| `batch_filter_unsupported` | `ws_batch_update` got a filter outside `attr == "value"`; nothing was staged | Rewrite as one `attr == "value"` condition, or stage per record with `ws_multi_update` (4.5) |
| `batch_filter_unknown_attribute` / `batch_update_unknown_field` | The filter attribute is on no loaded record / the field is not in the object-structure schema (the loaded records when there is no schema); nothing was staged | Check the name (`maximo://os/{osName}/schema`); select the filter attribute in `os_query_builder` and reload |
| `batch_update_missing_value` / `batch_update_invalid_value` | `ws_batch_update` had no `value`, or one that cannot become the attribute's type; nothing was staged | Send a valid `value` (a plain decimal for numeric fields; `true`/`false`/`1`/`0` for YORN) |
| `unknown_field` | `ws_update_field` / `ws_multi_update` got a name that is not an attribute of the object structure; nothing was staged | Check the name (`maximo://os/{osName}/schema`) |
| `field_not_updatable` | A system or identity key (`href`, `localref`, `_rowstamp`, `_id`, `*_collectionref`, the unique id) was sent to `ws_update_field` / `ws_multi_update` / `ws_batch_update`; nothing was staged | Drop it: these are not attributes |
| `use_change_status` | `status` was sent to a field-update tool; nothing was staged | `maximo_plan_status_change` then `maximo_change_status` (4.8, R14) |
| `relation_field` / `batch_update_relation_field` | A plain value was sent to a child collection (e.g. `worklog`); nothing was staged | `ws_add_child_record` / `ws_remove_child_record` (4.6) |
| `batch_update_key_field` | `ws_batch_update` was asked to set a primary-key attribute (e.g. `wonum`, `siteid`) on many rows; nothing was staged | Do not batch key changes; change one record with `ws_update_field` if really needed (Maximo decides) |
| `some_updates_refused` | `ws_multi_update`: some fields were refused, the rest are staged | Read `result[].error`; fix or drop those fields, then preview |
| `needs_confirmation`                                                                                                | `ws_commit` was asked to confirm                          | Show the staged changes; recommit with `confirmed:true` after yes            |
| `commit_failed` / `commit_partial_failure` / `commit_aborted`                                                       | Maximo rejected the commit (or part of it)                | Quote each `error.maximo_errors[].reasonCode` + `message`; fix; build a fresh working set (R10). If `error.outcome` is `unknown`, do NOT retry -- verify in Maximo first |
| `locked`                                                                                                            | A commit on this working set is still running             | Poll `ws_commit_status` (with `asyncId` if you have it); never re-commit (R16) |
| `server_busy`                                                                                                       | The server's parallel-call limit was reached              | Retry in a few seconds                                                       |
| `no_next_page` / `no_previous_page`                                                                                 | Maximo returned no such link                              | You are at the end; tell the user                                            |
| `commit_outcome_unknown` | The server restarted during this working set's commit; Maximo may or may not have applied it | Do NOT commit again. Check the records with `os_query_builder`, tell the user, then `ws_discard` and re-stage only what is missing (a reload alone keeps the hold) |
| `unstaged_changes_block_paging`                                                                                     | Staged changes exist                                      | `ws_commit` or `ws_discard`, then page                                       |
| `status_change_not_allowed`                                                                                         | The action is not currently allowed                       | Show `allowed_actions`; ask the user                                         |
| `invalid_target_status`                                                                                             | The status is not a valid next status for this record     | Offer one of the returned `valid_next_statuses`                              |
| `input_node_reached`                                                                                                | The workflow needs a choice only the Maximo UI accepts    | Tell the user to finish it in the Maximo Inbox; the assignment stays open    |
| `assignment_not_active`                                                                                             | The assignment was already completed or reassigned        | Re-read with `maximo_get_workflow_assignments`; tell the user                |
| `process_not_active`                                                                                                | The workflow process is not active or not for this object | Report it; ask the user which process to use                                 |
| `workflow_call_failed`                                                                                              | Maximo refused the workflow call                          | Quote Maximo's message; do not retry the same call                           |
| `confirmation_required`                                                                                             | A configuration tool needs `confirm:true`                 | Show the user what will happen; call again with `confirm:true` after a yes   |
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
- A working set holds loaded records and staged changes. It expires after inactivity (sliding
  timeout). On `ws_not_found`, rebuild it. If the server runs with working-set persistence, a set
  also survives a server restart -- keep using the same id.
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
   `commit_failed` in 3.3; never reuse the working set (R10) and stop after two failed
   attempts, reporting the fields and reasons.

### 4.5 Update existing records

1. `os_query_builder` + `ws_load` the records.
2. `ws_set_active` with `restID:"0"` (a 0-based index is simplest), then `ws_get_active` to
   confirm it is the right record. Or pass `restID:"active"` / the record's restId directly.
3. Stage: `ws_update_field` (one field), `ws_multi_update` (`updates:[{restID, fields:{...}}]`,
   several fields or records), or `ws_batch_update` (`spec:{field, value, filter?}` for one value
   across many rows). `filter` is ONE condition, `attr == "value"` (`status == "WAPPR"`; single
   quotes or an unquoted value without spaces also work). The attribute name is matched
   case-insensitively and must be on the loaded records (select it); the value must match
   exactly. Any other form (AND/OR, `!=`, `<`, `>`) is refused with `batch_filter_unsupported`
   and nothing is staged. Omitting `filter` stages the update on ALL loaded rows, so always check
   in `ws_preview_changes` that only the intended rows were staged. `field` (any case) and
   `value` are both required; a primary-key attribute (`wonum`, `siteid`, ...) is refused
   (`batch_update_key_field`); the value is converted to the attribute's type (numbers: plain
   decimals only; YORN: `true`/`false`/`1`/`0`). The result
   reports `matched`, `staged` and `unchanged` (rows that already held the value). There is no
   `spec.updater`.
4. `ws_preview_changes` -> before/after to the user -> yes -> `ws_commit`.
5. Never stage a status through a field-update tool (R14) -- `status` is refused with
   `use_change_status`, and so are system keys (`field_not_updatable`) and a plain value onto a
   child collection (`relation_field` / `batch_update_relation_field`). Never stage readOnly fields.

### 4.6 Child rows and deletes

- One child row: `ws_add_child_record` (`id`, `restID` of the parent, `field` = the relationship
  array name from `relatedObjects`, `record` = the row) or `ws_remove_child_record` (`id`, `restID`,
  `field`, then `keyValues` OR `index`).
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
   nothing. Show the user: current status, requested status, whether it is allowed, and
   `valid_next_statuses` (Maximo's own list for this record). If the verdict is BLOCKED, offer one
   of those statuses instead -- do not call `maximo_change_status` with the blocked one.
3. Only after a yes: `maximo_change_status` with the same values. Optional `memo` (50 characters
   at most -- Maximo rejects more), optional `statusDate` (ISO 8601; omit it for "now" -- Maximo then uses its own clock).
4. The status action name differs by object structure (for example `changeWOStatus`); the plan
   returns it as `detected_action` -- pass that as `actionName`. Omitted, it is detected again.
   Single record only.
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

1. `maximo_get_workflow_assignments` -- OPEN assignments by default (`status:"ALL"` for every
   status; filter with `ownerId`, `personId`, `processName` ...). Only assignments the API user can
   see are listed. Each has `assignmentId`,
   `task`, `owner` (table, id, description) and `onAccept` / `onReject` (the two routes).
2. Show the user the task, the owning record and both routes; ask which way to route it.
3. `maximo_complete_workflow_assignment` with `assignmentId`, `accepted` (true = onAccept,
   false = onReject) and a `memo` -- WITHOUT `confirm` first (nothing is sent), then the same call
   with `confirm:true`.
4. `input_node_reached` means the next step needs a choice Maximo only accepts in its UI: tell the
   user to finish it in the Maximo Inbox (the assignment stays open). Do not retry the same call;
   route the other way (`accepted:false`) only if the user asks.
5. To START a process on a record: `maximo_start_workflow` (`osName`, `restId`, `processName`),
   plan first, then `confirm:true`.
6. `maximo_send_workflow_response` is for workflows that expose actions on the owning record
   itself (its `osName` and the record's rest id) -- not for normal assignment routing.

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
attachment's `describedBy.identifier` or its `href`. To add one: `ws_add_attachment` (`id`,
`restID`, `fileName`, `text` or `contentBase64`, optional `mimeType`, `description`, `docType`) --
not staged, so plan first and `confirm:true` after a yes. Files over the server's limit
(`MCP_MAX_ATTACHMENT_MB`, default 25) are refused.

### 4.14 Field values, aggregation, reports, Maximo diagnostics

- Valid values for a field: `maximo_lookup_values` (`osName`, `attribute`; `setupdata` for a new
  record's context such as `{"siteid":"BEDFORD"}`, or `restId` for an existing record; `search` to
  narrow). Use it instead of guessing domain values (R12) -- it also covers table fields.
- "How many / how much per ...": `maximo_aggregate` (`osName`, `groupBy`, `aggregates` such as
  `{fn:"sum", attribute:"estlabhrs"}`, `where`, `orderBy`). count is always included.
- Reports: `maximo_list_reports` (`osName`), then `maximo_run_report` (`osName`, `reportName`
  ending in `.rptdesign`, `where`, optional `format` -- pdf by default); the file comes back as an
  embedded resource. Reports over `MCP_MAX_REPORT_MB` (default 10) are refused.
- `where` on `maximo_aggregate`, `maximo_run_report` and `maximo_lookup_values` is a RAW OSLC
  string such as `siteid="BEDFORD" and status="WAPPR"` -- not the `{conditions:[...]}` object of
  `os_query_builder`.
- Integration failures: `maximo_integration_errors` (`view` errors or tracking).
- Maximo's own server log (if enabled): `maximo_read_server_log` (`minLevel`, `contains`,
  `sinceMinutes`). This is Maximo's log, not this server's (`mcp_read_logs`).

### 4.15 Automation scripts

Only run a script the user named or approved. `maximo_invoke_automation_script` runs it at once
with no preview, and a script can change data even on GET.

- `scriptName`, optional `params` (query string).
- Outside read-only it also takes `httpMethod:"POST"` and a JSON `body` (the script reads it as
  `request`). A read-only server with script-get enabled accepts GET only.
- `op_success` is true on a 2xx; `httpStatus` and `body` carry the script's answer. Some scripts
  return very large bodies; narrow them with `params` where the script allows.

### 4.16 Anything else that is a read: `maximo_get_url`

Use it only when no dedicated tool fits, for example `/api/whoami`, a child collection `href`,
or `/api/error/messages/<code>`.

- `url` is a path on this Maximo (`/api/os/mxapiwo?oslc.pageSize=5`) or a full URL on the same
  host. Add `params` and `headers` if needed; `maxBytes` caps the body (default 200000).
- GET only, same host only, no redirects followed, credential headers refused. JSON comes back
  parsed; large bodies are truncated and binary bodies omitted (use `ws_get_attachment`).
- It refuses `action=` parameters and `/api/script` paths because those can change data. Use
  `maximo_invoke_action` / `maximo_invoke_automation_script`. Do not try to disguise them.
- For record queries prefer `os_query_builder` + `ws_load`; they validate and feed the working set.
- Use `/api/...` paths. On MAS, `/oslc/...` redirects API-key callers to the login page
  (`AUTH_REDIRECT`).

### 4.17 Audit and diagnostics

`maximo_get_audit_logs` (filters: `fromTs`, `toTs`, `wsId`, `osName`, `operation`) lists working
set create/update/delete/commit events; it needs `AUDIT_ENABLED=true` on the server.
`mcp_server_status` (always available) reports version, sync progress, configuration and the
tools the server withholds; `mcp_read_logs` tails this server's log (dev mode / read-only).

### 4.18 Configuration tools (only with `--copilot-mode`)

These run automation scripts inside Maximo and change configuration, so they belong in development
environments. Each one checks Maximo's own permissions; a refusal is final (golden rule 7).

- `maximo_dbconfig_status` / `maximo_dbconfig_apply_status`: read-only -- configuration level
  (`NONE` / `NONSTRUCT` / `STRUCT`), Admin Mode state, pending changes, apply progress.
- `maximo_dbconfig_apply`: applies pending database configuration. Show the user the status first;
  then `confirm:true` AND `confirmToken:"APPLY"`. Only `STRUCT` changes need Admin Mode.
- `maximo_dbconfig_discard`: drops PENDING configuration only; `confirm:true` after a yes.
- `maximo_admin_mode` (`action` on / off / cancel): affects every user; `confirm:true` after a yes.
- `maximo_system_property` (`get` / `list` / `set`): `set` needs `confirm:true`.
- `maximo_sql_query`: a single read-only `SELECT`; give a `reason` and `confirm:true` after the user
  approved the SQL.
- `maximo_reload_cache`: reloads a Maximo cache live.
- `maximo_appdesigner_edit`: edit an app's presentation by delta -- `init` -> `modify` -> `preview`
  -> `commit` (`confirm:true` after a yes) -> `verify`. A server restart is needed before the UI
  shows it.
- `maximo_copilot_setup`: installs / inspects / removes the utility scripts (`mode`, `dryRun`
  defaults to a dry run). An administrator must still grant the signature options.

---

## 5. Query reference (`os_query_builder`)

`opAction` is `"query"`. `osName` is required. `lean` defaults to true; leave it.

### 5.1 where

Conditions are ANDed; set `orMode:true` for OR.

    { "conditions": [ { "field": "siteid", "op": "=", "value": "BEDFORD" },
                      { "field": "status", "op": "in", "value": ["WAPPR","APPR"] } ] }

- ops: `=`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `like` (value `"%pump%"`), `isnull`, `isnotnull`
  (no value needed; they render as `attr!="*"` and `attr="*"`)
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

         "childCollection": { "parentRecordId": "<restId or href>", "relationship": "asset", "responseOs": "MXAPIASSET" }

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

NOT here -- do not attempt: aggregation inside `os_query_builder` (`_dbcount`, `_dbsum`, ... on a
related set are silently dropped) -- use `maximo_aggregate` for group-by counts and sums; and
and/or nesting inside `oslc.where`. `savedQuery` is case-sensitive, is ANDed with `where`, and a
KPI is `KPI:<name>`; names come from `queryCapability` in `maximo://os/{osName}`. `pageSize` is
capped by the server (`MCP_MAX_PAGE_SIZE`, default 1000) -- page instead.

### 5.6 Reading `ws_load` (and `ws_get_records`, `ws_next_page`, `ws_previous_page`)

Always set `useLean:true`. A lean payload carries `### SCHEMA` (short key -> full field name) and
`### DICT` (`*N` pointer -> repeated string). Decode BOTH before presenting data. Hrefs and ISO
dates are never encoded.

`meta` fields: `count` (rows in this page), `totalCount` (matching rows in Maximo -- needs
`collectioncount` or `count`), `hasMore` (more pages remain), `paging` (`pagenum`, `totalPages`,
`nextPage`, `previousPage`), `schema` (with `addschema`). Quote `totalCount`, never `count`.

### 5.7 Strict-schema servers

With `--strict-tool-schema` a few parameters change shape (no unions or nullables):

- `where` conditions: `value` is always a string; `in` uses `inValues:["WAPPR","APPR"]`.
- `select` is a plain string array; child blocks go in `childSelects:{ "worklog": ["description"] }`
  and aliases in `selectAliases:[{ "attr": "asset.description", "as": "assetdesc" }]`.
- `ws_update_field` takes `stringValue` or `numericValue` instead of `field_value`.
- `ws_multi_update` entries take `stringFields` / `numericFields` instead of `fields`.

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

R6. Working set ids expire. On `ws_not_found`, rebuild with `os_query_builder` and continue. If
the expired set held staged, uncommitted changes, tell the user they were lost before re-staging.

R7. Route workflow assignments with `maximo_complete_workflow_assignment` and the
`assignmentId` from `maximo_get_workflow_assignments` -- never by changing the record's status or
fields. `maximo_send_workflow_response` acts on the owning record, not on an assignment.

R8. Prefer `maximo://os/...` URIs. The only `maximo://object/...` URI you may use is
`.../relationships/compact`, to name a relationship `relatedObjects` omits. Any other
`maximo://object/...` bypasses object-structure security.

R9. Never send readOnly fields in `ws_update_draft`, `ws_update_field` or `ws_multi_update`.

R10. Never reuse a working set after a failed commit. Build a fresh one (`ws_init_new_record` for
a create).

R11. In `ws_update_draft`, pass the draft's `_tempId` as `temp_id`, not inside `record`.

R12. For domain-constrained fields, look the value up (`maximo_lookup_values`) or omit it --
never guess. `ws_preview_changes` flags it in `validation_warnings` (`invalid_domain_value`) and
Maximo rejects it at commit with a BMXAA code.

R13. Never `ws_commit` without `ws_preview_changes` and the user's confirmation first.

R14. Never change a status with `ws_update_field`, `ws_multi_update` or `ws_batch_update` (they
refuse it: `use_change_status`). Use `maximo_plan_status_change` then `maximo_change_status`.

R15. If `ws_commit` returns `{ async: true, asyncId }` the commit is NOT finished. Poll
`ws_commit_status` (about every 30 s) until it reports `succeeded`, `failed` or `interrupted`, and
report success only on `succeeded`. If you do not have `ws_commit_status` (an older server),
`ws_commit` completes before it responds and its result is final.

R16. Never re-commit after a `ws_commit` timeout. The working set stays locked while the commit
runs and a retry is refused. If you lost the `asyncId`, call `ws_commit_status` with the working
set id. A `ws_commit_status` of `interrupted`, or a `ws_commit` refusal with
`commit_outcome_unknown`, means the server restarted mid-commit: verify in Maximo first, never
just retry.

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

R22. When you are finished with a working set, `ws_remove` it -- also on a read-only server.
