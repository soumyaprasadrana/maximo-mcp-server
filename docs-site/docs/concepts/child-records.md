# Child Records

Many Maximo Object Structures expose **child collections** — arrays of related rows on a parent record. Examples: `synonymdomain` on a domain, `alndomain` on `DMMAXDOMAIN`, `workorderspec` on a work order, `worklog` on a service request.

Editing these safely is subtle, so the Working Set gives child collections first-class, natural-key-aware handling.

## The problem with full-array replacement

Maximo's OSLC PATCH matches child rows by their **natural key** (the `pk` fields in the child's sub-schema) and merges. If you PATCH a child field by submitting the *entire* replacement array, any existing row you forget to include can be silently dropped. Reconstructing every row's key fields by hand is a footgun.

## The solution: targeted child tools + action diffing

Two tools let you change **one** child row without resubmitting the whole array:

### `ws_add_child_record`

Append a single child row.

```
ws_add_child_record
  id      = <wsId>
  restID  = "active"        # parent record (or a restId/href)
  field   = "alndomain"     # the relationship/child-array field
  record  = { value: "D", description: "Type D" }
```

### `ws_remove_child_record`

Remove one child row by its natural-key values **or** its array index.

```
ws_remove_child_record
  id        = <wsId>
  restID    = "active"
  field     = "alndomain"
  keyValues = { value: "N" }     # …or  index: 3
```

Both validate that the target field really is a relation-typed child array and fail clearly otherwise. Under the hood they reuse the same staging path as a field update, so the preview/commit flow is unchanged.

## How changes are computed — per-row `_action`

At preview and commit time, the submitted child array is **diffed against the originally loaded snapshot**, matched by natural key. Each row that actually changed is emitted with a Maximo per-row action, and **untouched rows are omitted entirely**:

| Situation | Result |
| --- | --- |
| Key present only in the new array | `_action: "Add"` |
| Key in both, a field value differs | `_action: "Change"` (key + changed fields only) |
| Key in both, identical | *omitted* — never round-trips |
| Key present only in the original | `_action: "Delete"` (carries its key) |

So adding row **D** and removing row **N** from a 4-row collection produces exactly two outgoing rows — `D` as `Add` and `N` as `Delete` — leaving `A`, `B`, `C` untouched. This is safer *and* smaller than a blind replace.

::: tip Verb note
Because the commit path is a single-resource **PATCH MERGE**, modified rows use `"Change"` (per IBM's *Create & Update* REST semantics). The BULK path's `"Update"` verb is a different context. The verbs are centralized so they can be adjusted in one place if your instance expects otherwise.
:::

## Natural keys and child-local matching

A child sub-schema's `pk` is the full composite key and can include columns **inherited from the parent** (e.g. `domainid`, `siteid`, `orgid`) that never appear on the child rows themselves in an OSLC child array. The diff resolves the **child-local** subset of the key — the `pk` columns actually present on the rows — and matches on that. This is what lets a removed row be correctly paired with its snapshot and emitted as a `Delete`.

## Preview shape

For child fields, `ws_preview_changes` shows only the changed rows, each labelled with its computed `_action` — not a full before/after array. Scalar (non-child) fields keep the usual `before` / `after` diff.

## Missing-key warning

If a submitted child row is missing one or more of its natural-key fields, `ws_preview_changes` adds a non-blocking `child_missing_natural_key` warning: Maximo will match by natural key, and rows missing key fields may be treated as new inserts. Provide the key fields to get precise Add/Change/Delete behavior.

## Nested child structures (child-of-child)

Some Object Structures expose **grandchild** collections — child rows that themselves carry child arrays. Examples: `maxsyskeys` under `MAXSYSINDEXES`, or similar structural hierarchies.

The diff engine automatically discovers and recursively tags grandchild rows with their own `_action` values, ensuring MERGE semantics work correctly at nested levels. You don't need special handling — add/remove grandchildren the same way as direct children, and the preview/commit path handles the nesting.

## Creating a record with children

For a brand-new record, use the create flow (`ws_init_new_record` → `ws_update_draft`). Child arrays are fully supported there — pass them directly in the draft's fields:

```
ws_update_draft
  id      = <wsId>
  temp_id = <draft tempId>
  record  = {
    description: "New WO",
    workorderspec: [ { assetattrid: "VOLTAGE", alnvalue: "220V" } ]
  }
```
