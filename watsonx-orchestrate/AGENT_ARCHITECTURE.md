# Maximo MCP Agent Architecture

## Goal
Build a reliable multi-agent architecture for Maximo where:
- core agents own MCP tools directly and are self-contained,
- process agents hold all domain/object-specific knowledge,
- failures never produce fabricated business data.

## Layer Model

### 1) Tools Layer
MCP tools exposed by `maximo-mcp-remote`.

### 2) Core Layer (tool owners)
Each core agent owns its MCP tools directly. The only collaborator is `maximo_metadata_agent`,
called only when `context.osName` is not already provided by the caller.

| Agent | Tools owned | Phase pattern |
|---|---|---|
| `maximo_metadata_agent` | maximo_get_metadata, ctx_get, ctx_set | On-demand support |
| `maximo_read_agent` | os_query_builder, ws_load, ws_get_records, ws_remove, ctx_get, ctx_set | Single phase |
| `maximo_create_agent` | ws_init_new_record, ws_add_record, ws_preview_changes, ws_commit, ws_discard, ws_remove, ctx_get, ctx_set, ctx_remove | prepare → commit |
| `maximo_update_agent` | os_query_builder, ws_load, ws_set_active, ws_multi_update, ws_preview_changes, ws_commit, ws_discard, ws_remove, ctx_get, ctx_set, ctx_remove | prepare → commit |
| `maximo_status_agent` | os_query_builder, ws_load, ws_get_records, ws_remove, maximo_plan_status_change, maximo_change_status, ctx_get, ctx_set | plan → execute |
| `maximo_workflow_agent` | maximo_get_workflow_assignments, maximo_send_workflow_response, ctx_get, ctx_set | list → execute |

### 3) Process Layer (ctx_* only)
Process agents own the user conversation and delegate all Maximo operations to core agents.
They hold all domain/object/field knowledge — core agents hold none.

- `example_create_sr_agent`, `example_read_sr_agent`, `example_update_sr_agent`
- `maximo_asset_assistant`, `maximo_wo_progress_analyzer`
- Any future domain-specific or workflow-specific agents

Process agents may call ONLY `ctx_create`, `ctx_get`, `ctx_set`, `ctx_delete` as MCP tools.

## Contract Rules

### osName shortcut (critical)
If `context.osName` is already in the incoming message, core agents skip `maximo_metadata_agent`
for `resolve_os` entirely. Process agents should always pre-seed `osName` in `initial_context`
to avoid unnecessary metadata hops.

### Two-phase execution (create / update / status / workflow)
Write operations are split into two phases separated by explicit user confirmation:
- **Phase 1** (prepare / plan / list): stage the operation, return preview. STOP. Do not write.
- **Phase 2** (commit / execute): read staged state from ctx, apply. Never re-stage.

State is bridged via ctx between phases:
- `draft.wsId` — create and update
- `draft.restId` — status
- `draft.ownerid` — workflow

### Core agent independence
- Core agents hold ZERO object-specific or domain-specific field knowledge.
- All field names, domain values, and business rules live in process agents.
- Core agents pass `task.record` / `task.updates` / `task.newStatus` / `task.actionName` as-is.

### Collaborator call format (critical)
Every collaborator tool call has exactly ONE parameter: `message` (a JSON string).
```
chat_with_collaborator_<agent>(message='{"session_id":"...","context":{...},"task":{...}}')
```
Omitting `message` causes a validation error every time.

### Global reliability
- Hard fail on any tool or collaborator error.
- Return the error payload unchanged — never wrap or reinterpret.
- No fabricated records, status changes, workflow actions, or computed facts.

## Delegation Flows

### Read
```
process → read_agent:
  ctx_get → (resolve_os if osName unknown) → os_query_builder → ws_load → ws_get_records → return records
```

### Create
```
process → create_agent (prepare):
  ctx_get → ws_init_new_record → ws_add_record → ws_preview_changes → return preview_ready

process → create_agent (commit):
  ctx_get draft.wsId → ws_commit → return created
```

### Update
```
process → update_agent (prepare):
  ctx_get → os_query_builder → ws_load → ws_set_active → ws_multi_update → ws_preview_changes → return preview_ready

process → update_agent (commit):
  ctx_get draft.wsId → ws_commit → return updated
```

### Status
```
process → status_agent (plan):
  ctx_get → os_query_builder → ws_load → ws_get_records → extract restId from href → ctx_set draft.restId
  → maximo_plan_status_change → return plan_ready

process → status_agent (execute):
  ctx_get draft.restId → maximo_change_status → return status_changed
```

### Workflow
```
process → workflow_agent (list):
  ctx_get → maximo_get_workflow_assignments(includeAllowedActions=true)
  → ctx_set draft.ownerid → return assignments_ready

process → workflow_agent (execute):
  ctx_get draft.ownerid → maximo_send_workflow_response → return workflow_actioned
```

## Obsolete Files
Kept in `watsonx-orchestrate/agents/obsolete/` for reference.
These were the original tool/action layer, superseded by the merged core agent design.
Restore as a separate tool layer if a 3-layer separation is needed in the future.

| File | Was responsible for |
|---|---|
| `maximo_ws_agent` | All ws_* operations, LEAN decode, working set lifecycle |
| `maximo_query_builder_agent` | Query payload construction and validation |
| `maximo_status_action_agent` | Status plan and change tools |
| `maximo_workflow_action_agent` | Workflow assignment and response tools |

## Deployment Order
1. `maximo_metadata_agent`
2. Core agents: `maximo_read_agent`, `maximo_create_agent`, `maximo_update_agent`, `maximo_status_agent`, `maximo_workflow_agent`
3. Process agents and examples

## Cleanup Scope
Cleanup removes: metadata_agent, all core agents, all example/process agents, MCP toolkit, connection.
Obsolete agents are not deployed and require no cleanup entry.
