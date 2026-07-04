# Working Set Model

A **Working Set** is a stateful, in-memory transaction tied to a query context. It is the heart of how this server writes to Maximo safely: nothing is sent until you explicitly commit, and you always get a reviewable preview first.

## Lifecycle

```
os_query_builder   →  creates the Working Set (returns a wsId)
ws_load            →  fetch matching records into it
ws_set_active      →  choose the record to work on
ws_update_field    →  stage a change (in memory only)
ws_preview_changes →  review a diff + non-blocking validation warnings
ws_commit          →  apply to Maximo
ws_discard / ws_remove →  roll back staged changes / free the session
```

Every Working Set holds three views of its data:

- **original** — the snapshot loaded from Maximo (the baseline for diffs)
- **working** — the mutable copy your staged edits are applied to
- **change log** — the staged create/update/delete operations

## Staging, not writing

`ws_update_field`, `ws_multi_update`, `ws_batch_update`, `ws_init_new_record` → `ws_update_draft`, `ws_delete_record`, and the child tools all **stage** changes. They mutate the working copy and record the intent — they do not call Maximo.

## Preview before commit

`ws_preview_changes` returns a field-level diff of what will be sent, plus a **non-blocking** validation pass:

- Domain-value checks, read-only flags, type checks, and missing natural-key warnings are returned under `validation_warnings` with a `validation_note`.
- These are **advisory**. They do not block commit. Show them to the user and let them decide.

```json
{
  "op_success": true,
  "changes": [
    { "type": "update", "restID": "1234", "changes": [
      { "field": "status", "before": "WAPPR", "after": "APPR" }
    ]}
  ],
  "validation_warnings": [ /* … */ ],
  "validation_note": "Non-blocking warnings — review before committing."
}
```

## Commit

`ws_commit` plans the staged changes and executes them against Maximo:

- Small change sets go out as individual **PATCH / CREATE / DELETE** calls.
- Large change sets automatically switch to **BULK** mode (or force it with `forceBulk`).
- Maximo remains the final authority — `ws_commit` does not re-run the advisory validation.

On success the Working Set resets. Use `ws_discard` to drop staged edits while keeping loaded records, or `ws_remove` to free the session entirely.

## Session TTL

Working Sets are evicted after a period of inactivity (a sliding TTL, refreshed on each access). `ws_load` and `ws_set_active` return a `wsExpiresAt` timestamp so clients can see when the session will expire. After eviction, the next call returns `ws_not_found` — rebuild with `os_query_builder`.

## Active record

Most mutation tools act on the **active** record. Set it with `ws_set_active`, which accepts:

- a **0-based index** (`"0"`, `"1"`, … — easiest right after `ws_load`)
- a **`_tempId`** (for a draft created by `ws_init_new_record`)
- a Maximo **restId** or full **href**

## LEAN payloads

`ws_load` and `ws_get_records` accept `useLean=true`, returning a compressed representation that cuts token usage by **40–60%** on large result sets. The payload carries a `### LEAN FORMAT` header with a schema/dictionary to expand short keys; `href` and ISO dates are always kept raw. If compression wouldn't save tokens, it transparently falls back to plain JSON.

Next: how child collections are handled → [Child Records](/concepts/child-records).
