## Maximo MCP Tools — Usage Guidelines

These instructions define the orchestration logic for all Maximo MCP tools.
The tool schemas already describe parameters — this covers WHEN, WHY, and in
WHAT ORDER to call each tool, plus rules that prevent common failures.

---

## 1. PIPELINES

### READ

maximo_get_metadata → os_query_builder → ws_load → present results

### CREATE

maximo_get_metadata → ws_init_new_record → ws_add_record
→ ws_preview_changes → [user confirms] → ws_commit

### UPDATE

maximo_get_metadata → os_query_builder → ws_load → ws_set_active
→ ws_get_active → ws_update_field / ws_multi_update
→ ws_preview_changes → [user confirms] → ws_commit

### STATUS CHANGE

os_query_builder → ws_load → maximo_plan_status_change
→ [user confirms] → maximo_change_status

### WORKFLOW APPROVAL

maximo_get_workflow_assignments (includeAllowedActions: true)
→ [show user, ask which to action]
→ maximo_send_workflow_response

Skip maximo_get_metadata only if you already confirmed the OS name and field
names earlier in the same session.

---

## 2. maximo_get_metadata

Use these URI patterns in order:

maximo://os/search/{keyword} → find the OS name (start here)
maximo://os/{osName}/schema → parent field names for select + where
maximo://os/{osName}/relatedObjects → child entries; each has TWO names:
relationshipName → key for childOptions
objectName → dot prefix in where dot-notation
maximo://os/{osName}/subschemas/{child} → field names inside a child object

NEVER use maximo://object/... — bypasses OS-level security.

---

## 3. os_query_builder

opAction is always "query". osName is required.

### WHERE — parent record filtering

All conditions are AND by default. Set orMode: true for OR.

Equality / comparison:
{ "field": "siteid", "op": "=", "value": "BEDFORD" }
{ "field": "wopriority", "op": "<", "value": 3 }

In-list:
{ "field": "woclass", "op": "in", "value": ["WORKORDER","ACTIVITY"] }

Wildcard:
{ "field": "description", "op": "like", "value": "%pump%" }

Null checks (no value field needed):
{ "field": "assetnum", "op": "isnotnull" } → renders as assetnum=_
{ "field": "finishdate", "op": "isnull" } → renders as finishdate!=_

Date range (ISO 8601):
{ "field": "reportdate", "op": ">=", "value": "2025-01-01T00:00:00+00:00" }
{ "field": "reportdate", "op": "<", "value": "2026-01-01T00:00:00+00:00" }

Dot notation — filter PARENTS by child attribute value:
Use OBJECT NAME (not relationshipName) as the dot prefix.
{ "field": "ASSETSPEC.NUMVALUE", "op": ">", "value": 300 }

rawWhere — only when structured where cannot express the clause.
Completely overrides structured where. Use for mixed AND/OR nesting only.
"rawWhere": "siteid=\"BEDFORD\" and (status=\"APPR\" or status=\"INPRG\")"

### SELECT — fields to return

Plain field: "wonum"
With alias: "asset.description--assetdesc"
Child block: { "child": "assignment", "attrs": ["laborcode","craft"] }

### CHILDOPTIONS — filter child rows within each returned parent

Key = relationshipName (NOT objectName). Does NOT affect which parents return.

"childOptions": {
"assignment": {
"limit": 10,
"orderBy": { "rules": ["-scheduledate"] },
"where": { "conditions": [{ "field": "status", "op": "=", "value": "ACTIVE" }] }
}
}

### ORDERBY

Direction prefix mandatory. Plain field name without + or - is rejected.
"orderBy": { "rules": ["-wopriority", "+wonum"] }

### OTHER PARAMETERS

pageSize integer, default 20
collectioncount true → returns total record count
relativeuri true → shorter hrefs (recommended)
lean always true — do not change
basePath only set for legacy OSLC (/maximo/oslc/os)
leave unset for modern installs (default: /api/os)

---

## 4. ws_load

Always set useLean: true.

The lean response contains: ### SCHEMA → short key → full field name map ### DICT → \*N pointer → repeated string value map
Decode BOTH before presenting any data.

---

## 5. CREATE — ws_init_new_record → ws_add_record

Step 1: ws_init_new_record (osName)
Returns:
wsId — keep this for all subsequent calls
draftRecord — system defaults + \_tempId
metadata — per-field readOnly / required / constrainedValueList flags

Step 2: Read draftRecord and metadata BEFORE building your payload:

- readOnly fields in metadata MUST NOT be sent in ws_add_record
  Common readOnly on create: status, changeby, changedate, statusdate,
  problemcode, fr1code, fr2code, plusppoolnum, plusppoolitemnum
- System auto-set fields already in draftRecord — do not re-send:
  ticketid / wonum (&AUTOKEY&), class, reportdate, historyflag, actlabcost
- \_tempId from draftRecord MUST be included in ws_add_record — the engine
  uses it to match your payload to the draft slot

Step 3: ws_add_record
Send \_tempId + only the non-readOnly fields you explicitly want to set.

Domain-constrained fields (hasList: true or constrainedValueList in metadata)
must use values that exist in the Maximo domain. If unsure — OMIT the field
rather than guessing. A commit error of type "invalid_domain_value" means the
value is not in the allowed list for that field.

Step 4: ws_preview_changes → show user → wait for confirm → ws_commit

On commit success: status 201, location href contains the new record.
On validation_errors:
Each error has: type, attribute (field name), detail (reason).
Fix: remove/correct the offending fields, call ws_init_new_record again
(fresh wsId), re-add, preview, commit.
NEVER reuse a wsId after a failed commit.
NEVER retry more than twice — if still failing, report the field names
and reasons to the user and stop.

---

## 6. UPDATE — ws_set_active → ws_update_field / ws_multi_update

After ws_load, activate the target record:
ws_set_active: restID = "0" (0-based index, simplest form)

Then call ws_get_active to confirm the correct record is active.

Stage changes:
Single field: ws_update_field { field: "description", value: "..." }
Multi field: ws_multi_update { updates: { field1: val1, field2: val2 } }

NEVER update readOnly fields via ws_update_field.
NEVER update status via ws_update_field — use maximo_plan_status_change.

Then: ws_preview_changes → show before/after → confirm → ws_commit

---

## 7. STATUS CHANGE

Always call maximo_plan_status_change first. Show user: - Current status - Whether the requested transition is valid - All currently allowed transitions
Only call maximo_change_status after explicit user confirmation.

---

## 8. WORKFLOW

maximo_get_workflow_assignments:
Use includeAllowedActions: true to get valid action names in one call.

maximo_send_workflow_response:
osName = OS of the OWNING record (e.g. MXAPIWO) — NOT WFASSIGNMENT
restId = ownerid from the assignment — NOT the assignment's own ID
Omit actionName first to list allowed actions, then call again with
actionName to execute.

---

## 9. CRITICAL RULES — read every one

R1. childOptions key = relationshipName, NEVER objectName
Wrong: { "LABTRANS": {...} } Right: { "labtrans": {...} }

R2. Dot notation in where = objectName prefix, NEVER relationshipName
Wrong: "labtrans.TRANSTYPE" Right: "LABTRANS.TRANSTYPE"

R3. orderBy direction prefix is mandatory
Wrong: ["wopriority"] Right: ["-wopriority"]

R4. rawWhere silently overrides all structured where — never set both

R5. childOptions filters child rows only — does NOT filter parent records
To filter parents by child data → use dot notation in main where

R6. Working set IDs expire — on "working set not found" silently
re-run os_query_builder and continue

R7. ws_send_workflow_response targets the OWNING record
Use ownerid from assignment, not the assignment's own ID

R8. Never use maximo://object/... URIs — always maximo://os/...

R9. Never send readOnly fields in ws_add_record or ws_multi_update

R10. Never reuse a wsId after a failed commit — always ws_init_new_record again

R11. \_tempId from draftRecord must be included in ws_add_record

R12. For domain-constrained fields — omit rather than guess
A wrong value causes "invalid_domain_value" at commit time

R13. Never call ws_commit without ws_preview_changes + user confirmation first

R14. Never change status via ws_update_field — always use maximo_plan_status_change
