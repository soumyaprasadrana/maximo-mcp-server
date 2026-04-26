# Agent Context Pattern (Context Envelope v1)

## Purpose
Ensure session state is preserved across agent hops and conversation turns,
and that explicit user-provided values are never lost or overwritten by inference.

## Envelope
All process→core and core→metadata calls use:

```json
{
  "session_id": "<from ctx_create>",
  "context": {
    "entity": "asset|workorder|sr|...",
    "osNameHint": "MXAPIASSET",
    "osName": "MXAPIASSET",
    "objectName": "ASSET|SR|WORKORDER|...",
    "identifierField": "assetnum",
    "identifierValue": "7500",
    "siteid": "BEDFORD",
    "orgid": "EAGLENA",
    "requestedFields": ["*"],
    "requestedChildren": { "worklog": ["*"] }
  },
  "task": {
    "request_type": "read|create|update|...",
    "phase": "prepare|commit|plan|execute|list"
  }
}
```

The collaborator `message` parameter must be this JSON envelope serialized as a string.
Never pass prose or partial objects.

## Sticky Context Rules
- Carry explicit values (`identifierValue`, `siteid`, `osName`, etc.) forward unchanged.
- Do not drop or rewrite explicit values unless a tool call proves they are invalid.
- If a value is corrected, return both original and corrected in the error/response.

## Agent Responsibilities

### Process agents
- Call `ctx_create` once at the start of a new conversation. Store `session_id`.
- Call `ctx_set(session_id, { "request.<field>": value })` after every confirmed user input.
- Call `ctx_get(session_id)` before building phase calls — use ctx values, not memory.
- Pass `session_id` in every collaborator call.
- Call `ctx_delete(session_id)` on completion or cancellation.
- Never call `ctx_create` twice in the same conversation.

### Core agents
- Extract `session_id` from input as Step Zero. Return `session_id_required` error if absent.
- Call `ctx_get(session_id)` at the start of each request to refresh state.
- Pass `session_id` in every collaborator call to `maximo_metadata_agent`.
- Call `ctx_set` to persist phase state: `draft.wsId`, `draft.restId`, `draft.ownerid`.
- Call `ctx_set` on success to persist committed state: `committed.*`.
- Never call `ctx_create` or `ctx_delete`.

### maximo_metadata_agent
- Call `ctx_get` at start to check for cached `resolved.osName`.
- If `resolved.osName` and `resolved.schema_verified=true` exist in ctx, return from cache — skip API call.
- Call `ctx_set` after successful resolve to cache `resolved.osName`, `resolved.schema_verified`, `resolved.fields_summary`.

## ctx Key Conventions

```json
{
  "entity": "sr",
  "osNameHint": "MXAPISR",
  "resolved": {
    "osName": "MXAPISR",
    "objectName": "SR",
    "schema_verified": true
  },
  "request": {
    "siteid": "BEDFORD",
    "description": "Printer not working"
  },
  "draft": {
    "wsId": "WS-123",
    "_tempId": "TMP-001",
    "restId": "1234",
    "ownerid": "SR-5001"
  },
  "committed": {
    "ticketid": "SR1001",
    "recordId": "1234",
    "statusChanged": true,
    "workflowActioned": true
  }
}
```

## Phase Bridge (critical)
Two-phase operations (create/update/status/workflow) span separate conversation turns.
The ctx draft keys bridge state between phases:

| Operation | Phase 1 stores | Phase 2 reads |
|---|---|---|
| create | `draft.wsId`, `draft._tempId` | `draft.wsId` |
| update | `draft.wsId` | `draft.wsId` |
| status | `draft.restId` | `draft.restId` |
| workflow | `draft.ownerid`, `draft.osName` | `draft.ownerid` |

On phase 2 success: null out draft keys and write to `committed.*`.
On phase 2 failure: leave draft keys — caller can retry commit without re-staging.

## Failure Rule
On any failure, return:
```json
{
  "status": "error",
  "session_id": "<session_id>",
  "error": "<error_code>",
  "detail": "<actionable description>",
  "contextEcho": { "entity": "...", "osName": "...", "identifierValue": "..." }
}
```
Include `contextEcho` so callers can retry without losing explicit inputs.

## OS Resolution Guard
- Resolve OS using entity keywords (`sr`, `asset`, `workorder`), not record identifier values.
- Never invent shortened OS names (e.g. use `MXAPIASSET` not `ASSET`).
- If `context.osName` is provided by the caller, skip resolve_os entirely.
