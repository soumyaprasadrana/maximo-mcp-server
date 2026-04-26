# Process Agent Template Pattern

## What is a Process Agent?

A process agent is the top-most layer — the agent end users interact with directly.
It owns the conversation, manages the context session lifecycle, holds all domain/field
knowledge for its business scenario, and delegates all Maximo operations to core agents.
It never calls MCP tools directly except for context session management (ctx_*).

## Two-Layer Summary

| Layer | Agents | MCP tools | Purpose |
|---|---|---|---|
| **Process** | `example_*`, assistants | ctx_create, ctx_get, ctx_set, ctx_delete | Own session, gather user input, hold field knowledge, delegate to core |
| **Core** | maximo_read/create/update/status/workflow | ws_*, os_query_builder, maximo_plan/change_status, maximo_get/send_workflow, ctx_get, ctx_set | Own MCP tools, execute operations, cache state in ctx |
| **Support** | maximo_metadata_agent | maximo_get_metadata, ctx_get, ctx_set | OS resolution and schema lookup on demand |

> Core agents hold ZERO domain/field knowledge. All object-specific logic lives in process agents.

## Context Session Rules

### Process Agent Responsibilities
1. At the START of a new conversation: call `ctx_create` with entity-fixed `initial_context`.
   Pre-seed `resolved.osName` in `initial_context` to skip metadata lookup downstream.
2. After `ctx_create`: call `ctx_set` for any values the user provides upfront.
3. After every confirmed user input: call `ctx_set(session_id, { "request.<field>": value })` immediately.
4. Before calling a core agent: call `ctx_get(session_id)` to read back stored values.
   Use ctx values to build the collaborator message — do NOT rely on conversation memory alone.
5. Pass `{ session_id, context, task }` in every collaborator call.
6. On completion (commit or cancel): call `ctx_delete(session_id)`.
7. If `session_id` already exists in this conversation: NEVER call `ctx_create` again — reuse it.

### Core Agent Responsibilities
1. Extract `session_id` from input as Step Zero — error immediately if absent.
2. Call `ctx_get(session_id)` at start of each request.
3. Store phase state in ctx (`draft.wsId`, `draft.restId`, `draft.ownerid`).
4. Pass `session_id` to `maximo_metadata_agent` if called.
5. Never create, read outside phase state, or delete ctx sessions.

### maximo_metadata_agent Responsibilities
1. Call `ctx_get` to check for cached `resolved.osName`.
2. Return from cache if `resolved.osName` + `resolved.schema_verified=true` already exist.
3. Call `ctx_set` after successful resolution to cache the result.

## Standard Context Keys

```json
{
  "entity":   "sr | asset | workorder | po | ...",
  "osNameHint": "MXAPISR",
  "resolved": {
    "osName": "MXAPISR",
    "objectName": "SR",
    "schema_verified": true
  },
  "request": {
    "siteid": "BEDFORD",
    "orgid": "EAGLENA",
    "description": "...",
    "reportedpriority": "HIGH"
  },
  "draft": {
    "_tempId": "TMP-001",
    "wsId": "WS-123",
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

## YAML Template

```yaml
spec_version: v1
kind: native
name: <agent_name>
style: default
description: |
  <One sentence: what this agent does for the end user.>

instructions: |
  # Role
  <What you are and what you do for the user. One paragraph.>

  # CRITICAL — Collaborator Call Format
  Every collaborator tool call has exactly ONE parameter: "message" (a JSON string).
  You MUST always include "message". Omitting it causes a validation error every time.

  CORRECT:
    chat_with_collaborator_maximo_<core>_agent(
      message='{"session_id": "...", "context": {...}, "task": {...}}'
    )
  WRONG:
    chat_with_collaborator_maximo_<core>_agent()
    chat_with_collaborator_maximo_<core>_agent(session_id="...", task={...})

  # Session Lifecycle

  ## Session Init
  On the FIRST user message (no session_id exists yet):
  Call ctx_create with EXACTLY this initial_context — pre-seed osName to skip metadata lookup:
    {
      "initial_context": {
        "entity": "<entity>",
        "osNameHint": "<osName>",
        "objectName": "<objectName>",
        "resolved": {
          "osName": "<osName>",
          "schema_verified": true
        }
      }
    }
  Store the returned session_id. Use it for every ctx_* and collaborator call.
  If session_id already stored: never call ctx_create again — reuse it.

  ## Information Gathering
  <How to engage with the user. What questions to ask. What info to gather.>
  After each confirmed value, call ctx_set immediately:
    { "session_id": "<session_id>", "updates": { "request.<field>": "<value>" } }

  ## Phase 1 — Prepare / Plan / List
  Before calling the core agent: call ctx_get(session_id) to read all gathered values.
  Build the collaborator message from ctx — do NOT rely on conversation memory alone.

  EXACT message format:
  {
    "session_id": "<session_id — MANDATORY>",
    "context": {
      "entity": "<entity>",
      "osName": "<osName>",
      "osNameHint": "<osName>",
      "objectName": "<objectName>"
    },
    "task": {
      "request_type": "<create|read|update|status|workflow>",
      "phase": "<prepare|plan|list>",
      <operation-specific fields>
    }
  }

  Show the preview/plan/assignments to the user.
  Wait for explicit YES before proceeding to phase 2.

  ## Phase 2 — Commit / Execute
  After explicit user YES:
  Use the SAME session_id. The staged state is in ctx.
  {
    "session_id": "<same session_id>",
    "context": { "entity": "...", "osName": "...", "objectName": "..." },
    "task": { "request_type": "...", "phase": "<commit|execute>" }
  }

  ## After Completion
  - Tell the user the result.
  - Call ctx_delete(session_id).

  ## Error Handling
  - Return collaborator error payloads to the user in plain English.
  - For field-specific errors: offer to change or remove the field. Never re-prepare autonomously.
  - NEVER claim success if a write operation failed.
  - NEVER re-prepare without the user's explicit direction.

  ## On Cancellation
  - Tell the user nothing was changed.
  - Call ctx_delete(session_id).

guidelines:
  - display_name: "Session Init — Pre-seed osName"
    condition: "First user message, no session_id"
    action: >
      Call ctx_create with initial_context including resolved.osName and schema_verified=true.
      Store the returned session_id.

  - display_name: "No Duplicate Session"
    condition: "session_id already stored"
    action: "Reuse it. Never call ctx_create again."

  - display_name: "ctx_set After Every Confirmed Value"
    condition: "User confirms any piece of information"
    action: "Call ctx_set(session_id, { request.<field>: value }) immediately."

  - display_name: "Read ctx Before Phase 1"
    condition: "About to call phase 1"
    action: >
      Call ctx_get(session_id) to read all gathered values.
      Build the collaborator message from ctx — do NOT rely on conversation memory alone.

  - display_name: "osName Is Mandatory in Both Phase Calls"
    condition: "Calling any core agent"
    action: "Always include osName in context. Never omit it."

  - display_name: "Commit Uses Exact Same session_id"
    condition: "Phase 2"
    action: "Use the same session_id from phase 1. Staged state is in ctx."

  - display_name: "User Confirmation Between Phases"
    condition: "Phase 1 returns preview/plan/assignments"
    action: "Show result to user. Wait for explicit YES. Only then call phase 2."

  - display_name: "Error — Field-Specific Recovery"
    condition: "Phase 2 fails with a field rejection"
    action: "Tell the user which field failed. Offer to change or remove it. NEVER re-prepare on own initiative."

  - display_name: "Session Cleanup"
    condition: "Process completed or cancelled"
    action: "Call ctx_delete(session_id)."

  - display_name: "No Fabrication"
    condition: "Either phase fails"
    action: "Return error to user. Never invent a record ID or claim success."

tools:
  - maximo-mcp-remote:ctx_create
  - maximo-mcp-remote:ctx_get
  - maximo-mcp-remote:ctx_set
  - maximo-mcp-remote:ctx_delete

collaborators:
  - <core agents this process agent delegates to>
```

## New Agent Checklist

When creating a new process agent, copy the template and fill in:
- [ ] `name` — unique snake_case name
- [ ] `description` — one sentence, user-facing
- [ ] `entity`, `osName`, `objectName` — fixed for this agent's domain
- [ ] Information gathering section — what questions to ask, which ctx keys to set
- [ ] Phase 1 message shape — task fields specific to this operation
- [ ] Phase 2 message shape — commit/execute with same session_id
- [ ] Collaborators list — core agents only (`maximo_create_agent`, `maximo_update_agent`, etc.)
- [ ] Tools list — always the four ctx_* tools, nothing else
- [ ] Domain-specific field handling — validation, labels, user-friendly names
