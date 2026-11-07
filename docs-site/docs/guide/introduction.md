# Introduction

**Maximo MCP Server** is an enterprise [Model Context Protocol](https://modelcontextprotocol.io) server for **IBM Maximo Application Suite**. It gives AI agents a *governed* interaction layer over Maximo — one that understands Maximo metadata, builds valid queries, and never writes to Maximo without an explicit, reviewable commit.

It is published on npm as [`@soumyaprasadrana/maximo-mcp-server`](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server).

## Why not just call the REST API?

Letting an agent hit Maximo's OSLC REST API directly is risky and inefficient:

- It doesn't know which Object Structures exist, which fields are queryable, or how children relate to parents — so it guesses.
- A single wrong PATCH can overwrite or delete data with no preview step.
- Large result sets burn tokens.

This server solves those problems with three pillars.

### 1. Metadata Engine

A local SQLite-backed metadata store, synced from your Maximo instance, with keyword and (optional) vector search. Agents **discover before they act**: search for an Object Structure, read its schema, inspect child relationships and sub-schemas — all before building a query.

→ [Metadata Engine](/concepts/metadata-engine)

### 2. Validated Query Building

`os_query_builder` converts structured intent (`where`, `select`, `orderBy`, `childOptions`, `savedQuery`) into a metadata-validated OSLC URL and opens a **Working Set** session. For complex expressions that the structured schema can't fit, use `rawWhere` and `rawSelect` to pass raw OSLC directly. No unsafe hand-written queries.

### 3. Working Set transaction model

The Working Set is a **stateful, in-memory transaction**. Reads load records; every mutation is *staged*, not sent. A preview step shows a field-level diff plus non-blocking validation warnings. Only `ws_commit` writes to Maximo — and Maximo remains the final authority on data validity.

→ [Working Set Model](/concepts/working-set)

## What's in the box

| Capability | Summary |
| --- | --- |
| Metadata discovery | `maximo_get_metadata` over `maximo://` URIs — search, schema, related objects, sub-schemas |
| Query building | `os_query_builder` — validated OSLC, creates the Working Set |
| Staged CRUD | Load, update, multi/batch update, create (draft flow), delete, child add/remove |
| Preview & commit | `ws_preview_changes` (diff + warnings) → `ws_commit` |
| Status changes | Plan, then confirm -- checked against Maximo's valid next statuses and electronic signatures |
| Workflow | Open assignments with their routes, complete an assignment, start a process (plan, then confirm) |
| Answers | `maximo_aggregate` (group-by counts and sums), `maximo_lookup_values` (valid values for any field, incl. table domains) |
| Reports | `maximo_list_reports` / `maximo_run_report` -- BIRT reports as PDF |
| Attachments | List, fetch and upload (`ws_add_attachment`) record doclinks |
| Actions, import, scripts | Any allowed Maximo action, CSV/XML import with a preview, automation scripts, read-only GET of any Maximo URL |
| Operations | `maximo_integration_errors`; opt-in `maximo_read_server_log` |
| Configuration | Configure Database, Admin Mode, system properties, read-only SQL, cache reload, App Designer edits -- with `--copilot-mode` |
| Context store | Six `ctx_*` key-value tools for cross-tool agent state |
| OAuth 2.0 | Built-in authorization server for HTTP transport |
| Audit | Optional append-only log of every staged change |
| Diagnostics | `mcp_server_status` (always); `mcp_read_logs` with `--dev-mode` or `--readonly` |

## Design principles

- **Discover, then act.** Metadata first; no blind field names.
- **Nothing is silent.** Data changes go through a preview a human can read; the generic action and script tools, which do not, can be disabled.
- **Maximo is the source of truth.** Validation warnings are advisory; the server does not block commits on its own opinion.
- **Least surprise on children.** Child-collection edits are diffed by natural key so untouched rows are never disturbed. See [Child Records](/concepts/child-records).

Ready? → [Installation & Setup](/guide/getting-started)
