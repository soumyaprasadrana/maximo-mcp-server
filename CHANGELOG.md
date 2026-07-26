# Changelog

All notable changes to `@soumyaprasadrana/maximo-mcp-server` are documented here.

## 1.3.7 — 2026-07-26

### Added

- `rawSelect` parameter on `os_query_builder` for passing raw OSLC select strings when the structured schema doesn't fit.

### Fixed

- Nested child structures (child-of-child relations) now properly tagged during diff computation for correct MERGE semantics.

## 1.3.6 — 2026-07-26

(Skipped in favor of 1.3.7)

## 1.3.4 — 2026-07-26

Query builder enhancement + child handling improvements for nested structures.

### Added

- **`os_query_builder` now supports `rawSelect` parameter** for direct OSLC select-clause strings.
  Similar to the existing `rawWhere` parameter, `rawSelect` allows agents to pass raw OSLC select
  syntax to override structured `select` when complex field selections cannot be expressed via the
  standard `select` / `childSelects` / `selectAliases` schema.
  
  Use `rawSelect` when you need:
  - Complex nested child relationship selections: `wonum,description,status{*},assignment{laborcode,scheduledate}`
  - Wildcard expansions that the structured syntax does not cover
  - Full control over the OSLC select clause
  
  Available in both loose and strict tool schemas.

### Fixed

- **Grandchild (child-of-child) relation arrays now properly tagged with `_action`**.
  When staging changes to nested child collections (e.g., child-of-child like `MAXSYSINDEXES` → `MAXSYSKEYS`),
  the diff engine now discovers grandchild relation metadata and recursively tags all grandchild rows with
  their own `_action` (Add/Change/Delete). This ensures MERGE semantics work correctly on structural children.
  Previously, untagged grandchildren would cause Maximo PATCH errors (e.g., BMXAA9039E on index key updates).

- **Child collection diff behavior clarified with improved metadata tracking**.
  Enhanced `getChildRelationMeta()` to discover grandchild relations from the child subschema and cache them
  for `diffChildArray()` recursion. Added `GrandchildRelationMeta` interface for explicit grandchild tracking.

## 1.3.1 — 2026-07-18

Diagnostics fix, no behavioral changes to any tool schema or query/write logic.

### Fixed

- **`mcp_server_status` reported `version: "unknown"` under normal launch conditions.**
  It read only `process.env.npm_package_version`, which npm sets exclusively for
  processes it launches itself via `npm run <script>`. When an MCP client (Claude
  Desktop, Claude Code, etc.) spawns the server directly — the normal production
  path — that env var is never set, so the diagnostic always showed `"unknown"`
  regardless of the installed version. Extracted the existing, already-correct
  `package.json`-reading fallback (previously private to `server/index.ts`'s own
  `McpServer` version registration) into a shared `src/utils/version.ts` and wired
  it into `mcp_server_status` too.
- **`mcp_server_status`'s environment snapshot did not report `MCP_STRICT_TOOL_SCHEMA`**,
  making it hard to confirm at a glance which tool-schema mode (strict vs. loose,
  see 1.3.0) a running instance was actually using. Added it to the reported env keys.

## 1.3.0 — 2026-07-18

Reliability pass focused on cross-agent compatibility of `os_query_builder` and on a
data-safety gap found while validating an Application Designer (`DMMAXAPPS` /
`MAXPRESENTATION`) write path.

### Breaking

- **`os_query_builder.childOptions` restructured from a record to an array.**
  Previously `childOptions` was `record<relationshipName, ChildOptionSchema>`. It is
  now `Array<ChildOptionSchema & { relationship: string }>` — each entry now carries
  its own `relationship` field instead of being keyed by it.

  Before:
  ```json
  "childOptions": {
    "assignment": { "limit": 10, "orderBy": { "rules": ["-scheduledate"] } }
  }
  ```
  After:
  ```json
  "childOptions": [
    { "relationship": "assignment", "limit": 10, "orderBy": { "rules": ["-scheduledate"] } }
  ]
  ```

  **Why:** the record-of-object shape does not survive this MCP SDK's zod v4 →
  JSON-Schema conversion — the advertised `inputSchema` collapsed the nested value
  type to `additionalProperties: {}`, hiding `where`/`orderBy`/`limit`/etc. from any
  schema-driven tool-calling agent. This affected both the loose and strict tool
  schemas (strict mode's `.optional()`-only rewrite does not by itself fix
  dynamic-keyed records of objects; only `select`'s separate flattening to
  `childSelects` avoided it). An array of objects converts reliably. Real-world impact
  is expected to be low: the broken shape meant no schema-driven agent could have been
  reliably constructing `childOptions` calls in the first place.

### Fixed

- **Numeric fields now accept numeric strings.** `pageSize` and `childOptions[].limit`
  (`os_query_builder`, both schema variants), `numericValue` (`ws_update_field` strict),
  `numericFields` map values (`ws_multi_update` strict), and `index`
  (`ws_remove_child_record`, both variants) switched from `z.number()` to
  `z.coerce.number()`. Some MCP tool-calling bridges serialize numeric literals as JSON
  strings across the JSON-RPC boundary; strict `z.number()` hard-rejected those even
  though the schema advertised `type: number`. Coercion accepts both real numbers and
  numeric strings and does not weaken validation of genuinely non-numeric input.

- **Child-collection diffing no longer risks duplicate rows for singleton children
  with a fully parent-inherited primary key.** Some child objects (e.g.
  `DMMAXAPPS.MAXPRESENTATION`, whose only declared `pk` is `["app"]`, a parent-level
  column never present on the child row itself) had no child-local field for
  `diffChildArray` to match on. The previous fallback silently returned the raw
  submitted array with no dedup or `_action` tagging — if a caller used
  `ws_add_child_record` to update such a child, the working set's in-memory array could
  end up holding both the original row and the newly appended row, and committing that
  verbatim would create a duplicate record.

  Fixed by:
  1. `getChildRelationMeta` now also resolves the child subschema's generated
     `uniqueid` field (e.g. `maxpresentationid`) as metadata.
  2. `diffChildArray` tries the child-local natural key first, then falls back to
     `uniqueid` as a synthetic match key when the natural key resolves to nothing
     locally. This lets an existing singleton row be correctly matched and tagged
     `Change` instead of duplicated.
  3. If neither key resolves AND more than one row is submitted, the result is now
     flagged via `unsafeNoKeyMultipleRows`. `ws_preview_changes` surfaces this as a
     `child_no_usable_key_multiple_rows` warning, and the actual commit-diff path
     (`OSWSChange.applyChildActionsToDiff`) now throws rather than silently
     committing an ambiguous multi-row write.

### Internal

- Extended `childRelations_test.ts` with regression cases for the `uniqueid` fallback
  match, the genuinely-new-row Add path, the unsafe multi-row-no-key case, and the
  safe single-row-no-key passthrough.

## 1.2.3 and earlier

See git history — no changelog was maintained prior to 1.3.0.
