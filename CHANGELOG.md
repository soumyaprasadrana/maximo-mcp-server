# Changelog

All notable changes to `@soumyaprasadrana/maximo-mcp-server` are documented here.

## 1.5.0 -- 2026-08-03

### Added -- Configuration Safety Guards (new module: `src/maximo/guards/`)

A pluggable guard layer that runs between "compute the change set" and "send it to Maximo".
It exists for a specific class of hazard: configuration writes that Maximo **accepts without
error** while altering far more than the record you edited.

The founding case, measured on a live instance: adding ONE attribute with
`sameasobject`/`sameasattribute` but no `maxtype`/`length` caused Maximo to default the new
column to `ALN(50)` and then harmonise the entire Same As family to it -- staging IBM's own
`ASSET.ASSETNUM` from `UPPER(25)` to `ALN(50)` and flagging **217 attributes across 158
objects** for schema alteration. Each such commit took minutes purely because of the cascade,
and the commit reported success.

- **`sameas-parity` guard** (`DMMAXOBJECTCFG`). Same As means the attribute inherits Type,
  Length and Scale from the source -- the Database Configuration UI greys those fields out.
  Over REST nothing greys out, so the guard enforces it:
  - type/length/scale **omitted** -> **repaired** by inheriting the real values from the source
    attribute, and the repair is reported (never silent);
  - type/length/scale **supplied and different** -> **blocked**, naming the exact values required;
  - source attribute **not found** -> blocked (it would otherwise default to `ALN(50)`).
- Guards run in **both** `ws_preview_changes` (as blocking `guard_violations`) and `ws_commit`
  (where nothing is sent). A guard that fails to evaluate blocks rather than passing the change.
- Escape hatch `MCP_DISABLE_CONFIG_GUARDS=true` for emergencies; it re-opens the exact hole
  described above and logs a warning when used.
- Adding a guard is one file plus one line in `ALL_GUARDS` -- the engine calls them generically.

### Added -- Configure Database apply / discard / poll

The lifecycle no longer dead-ends at "click it in the UI". All three are actions on the existing
`MCPUTILS.DBCONFIG` utility, each additionally requiring the genuine IBM permission -- an MCP
grant can never substitute for it.

- `maximo_dbconfig_apply_status` -- READ-ONLY. One `phase`: `CLEAN` (nothing pending or running)
  / `PENDING` (staged, and whether Admin Mode is needed) / `RUNNING`, plus Maximo's own
  `configmessages`. Safe to poll; this is how you wait for an apply.
- `maximo_dbconfig_discard` -- `removeChanges`, OOTB `CONFIGUR.REMOVE`. Reverts everything
  PENDING; nothing applied is touched. The safe exit from an unintended cascade. Requires
  `confirm:true` and returns the pending set when refused.
- `maximo_dbconfig_apply` -- `runConfigDB`, OOTB `CONFIGUR.CONFIGURE`. ALTERS PHYSICAL SCHEMA.
  Requires `confirm:true` AND `confirmToken:'APPLY'`; the script itself refuses a STRUCT-level
  apply while Admin Mode is off, refuses while a run is in progress, and reports
  `nothing_to_apply` when the level is NONE. Asynchronous -- a success means STARTED.

Method signatures vary across Manage versions, so `removeChanges` is invoked through a small
resolver that tries the plausible arities and reports which worked, rather than guessing one.

### Added -- `maximo_sql_query` (read-only, human approval required)

Read-only SQL for diagnosis, backed by the new gated `MCPUTILS.SQLQUERY` utility
(`CONFIGUR.MCPSQLREAD`). This is the tool that found the cascade above.

Enforced server-side: a single statement only, `SELECT` / `WITH ... SELECT` only, every DML and
DDL keyword refused before the database is touched, results capped at 500 rows, connection
always released. The MCP tool additionally **refuses to run without `confirm:true`** and states
that approval is per query -- it can read any table, so results are treated as sensitive.

### Fixed

- **BULK/SYNC commits reported success while Maximo rejected rows.** These responses are a bare
  array of per-operation results and Maximo returns HTTP 200 for the batch even when individual
  rows fail; the object-shaped `oslc:Error` / `Error` checks could not see inside an array, so a
  partially (or entirely) failed bulk commit was normalized as data. `MaximoClient.parseResponse`
  now inspects every element and throws with the first BMXAA code plus failed/succeeded counts.
  Plain array payloads and normal collections still pass through unchanged. This matters most at
  scale, since the planner auto-switches to BULK at 50+ operations.

## 1.4.5 -- 2026-08-02

### Fixed -- the 300s ceiling that silently killed long commits

Node's global `fetch()` runs on undici with a **300s `headersTimeout`**. That ceiling is
invisible, cannot be raised from `RequestInit`, and `AbortSignal` can only shorten a timeout,
never extend one. A `DMMAXOBJECTCFG` object create routinely runs longer, so the server was
severing the connection while Maximo was still working -- and reporting it as a bare
`TypeError: fetch failed`.

Reproduced twice against a live instance with the identical payload:

```
code     : UND_ERR_HEADERS_TIMEOUT
elapsedMs: 304074      (earlier incident: 304524)
```

Maximo answered an unrelated query 378ms later, and the object was never created. The server
was not hung and Maximo was not silent: **we hung up on Maximo.**

- **New `httpAgents` module -- two connection pools, deliberately.** Configuration writes
  (create / update / delete / sync / bulk) ride a long-operation pool with no per-phase cap,
  bounded instead by an absolute `MAXIMO_COMMIT_TIMEOUT_MS` deadline (default 15 min). Reads
  and metadata keep a protective per-phase timeout, so one wedged GET still cannot hang
  forever. Both pools are per-origin connection-pooled and keep-alive'd.
- Pools come from the `undici` package with its own `fetch`, not the global one: Node bundles
  a private undici copy, and an Agent from the npm package is a different class that the
  bundled `fetch` may reject as a dispatcher. If the import fails the server degrades to
  global `fetch` and logs it, rather than failing to start.
- New config: `MAXIMO_COMMIT_TIMEOUT_MS` (900000), `MAXIMO_HTTP_TIMEOUT_MS` (300000),
  `MAXIMO_MAX_CONNECTIONS` (32).

### Fixed -- failures that reported themselves as successes

- **`OSWSCommitExecutor` returned `op_success: true` when operations failed.** With the
  default `abortOnError: false`, a commit in which *every* op threw still reported success --
  so the async job store recorded `succeeded` while carrying `ok: false`, and the engine then
  called `ws.reset()` and destroyed the staged draft. A commit is now successful only if every
  operation succeeded.
- **`MaximoClient` discarded `err.cause`.** `fetch()` collapses every transport failure into
  `TypeError: fetch failed` and hides the reason on `.cause` -- the difference between "we hung
  up on Maximo" and "Maximo hung up on us". Failures now carry a `transport` object with the
  error code, the real cause message, elapsed ms, and a plain-language interpretation, and are
  logged as `TRANSPORT FAILURE <method> <url> after <n>ms code=<code>`.
- **A failed commit was indistinguishable from a rejected one.** When no HTTP response was
  received, Maximo's actual outcome is unknown and the work may have completed server-side.
  Such commits are now marked `outcome: "unknown"` with an explicit instruction not to blindly
  retry, and to verify with `os_query_builder` first.

### Dependency

Adds `undici` (MIT, Node core team) -- the same client Node already runs beneath `fetch`.
It is required to construct a dispatcher; there is no way to raise the ceiling without one.

## 1.4.2 -- 2026-08-02

### Added -- asynchronous `ws_commit`

Commits on some object structures take longer than an MCP client will wait. Creating a
persistent object through `DMMAXOBJECTCFG` (one nested payload carrying `maxobjectcfg` +
`maxtablecfg` + every `maxattributecfg` + `maxsysindexes`) routinely runs **2-4 minutes**,
while clients abort the RPC at ~60s with `-32001 Request timed out`. The agent was then left
with no idea whether Maximo had succeeded, a working set locked by a commit that was still
running, and a retry that failed.

`ws_commit` now starts a job and answers immediately for object structures known to be slow:

```
ws_commit         -> { async: true, asyncId, workingSetId, osName, status: "running" }
ws_commit_status  -> running | succeeded | failed  (+ the full commit result)
```

- **`ws_commit_status`** (new tool) -- poll by `asyncId`, or by working set id when the
  asyncId was lost to a timeout. Returns the complete commit result once terminal, including
  the Maximo `BMXAA*` error on failure. Finished jobs stay pollable for 30 minutes.
- **Pluggable, not hardcoded.** The contract is identical for every object structure; which
  ones use it is configuration. `MCP_ASYNC_COMMIT_OS` (default `DMMAXOBJECTCFG`) takes a
  comma-separated list; an empty value disables async commits entirely. Adding another slow
  object structure later is a config change, not a redesign.
- **Everything else stays synchronous** -- domains, scripts, applications, business records.
  Per-call `forceAsync` / `forceSync` override the list for testing or one-offs.
- **Lock lifecycle.** The lock is held for the life of the job and released on the terminal
  state. A working set with a commit in flight is no longer evicted for inactivity, and
  `ws_remove` returns the `asyncId` rather than silently orphaning a running commit.

### Fixed

- A `locked` working set now says *why*: the response carries how long the lock has been held
  and the running `asyncId`, with the action `poll_ws_commit_status`. Previously it returned
  a bare `{ reason: "locked" }`, which read as a dead end after a timeout.
- `requireConfirmation: true` was accepted by `ws_commit` and then ignored, leaving callers
  waiting on a prompt that never came. It now fails fast with a `needs_confirmation` payload
  containing the staged changes; re-call with `confirmed: true` to proceed. Nothing is sent
  to Maximo in the meantime.
- `tool_reg_test` expected a `ws_add_record` tool that no longer exists (it is
  `ws_add_child_record`), so the suite reported a permanent failure.

## 1.4.1 -- 2026-07-30

### Added -- copilot utilities (opt-in, `MCP_COPILOT_MODE=true`)

A small set of permissioned Jython automation scripts (`MCPUTILS.*`) that close gaps the
Migration Manager / MXAPI object structures cannot reach, plus the tooling to install and
remove them. Nothing is installed until you ask for it.

- `maximo_copilot_setup` -- `status` (read-only, default) / `provision` / `uninstall`.
  Provision and uninstall are **dry run by default**; pass `dryRun:false` to write.
- `maximo_dbconfig_status` -- read-only Configure Database state: config level
  (`NONE`/`NONSTRUCT`/`STRUCT`), whether a run is in progress, Admin Mode state, Maximo's own
  config message stream. Note only `STRUCT` needs Admin Mode, so non-structural changes can be
  applied without disrupting users.
- `maximo_admin_mode` -- start/end Admin Mode, or cancel a stalled transition. Requires
  `confirm:true` **and** the genuine IBM `CONFIGUR.ADMINMODE` permission. Transitions are
  asynchronous -- poll `maximo_dbconfig_status`.
- `maximo_system_property` -- read/write system properties, closing the gap left by
  `DMMAXPROP` returning no rows. `set` requires `confirm:true` and reports `restartRequired`
  when the property is not live-refreshable.
- One-shot installer: start the server once with `MCP_COPILOT_SETUP=true`. On normal startup
  with `MCP_COPILOT_MODE=true` the server only **verifies and reports** -- it never writes.
  `MCP_COPILOT_AUTO_PROVISION=true` opts into writing on startup.

### Security model

Each script is gated by an `MCP*`-prefixed signature option added to an **existing OOTB app**
(`CONFIGUR` for Database Configuration utilities, `PROPMAINT` for properties) -- no new
application, no presentation, no navigation. Maximo's REST script handler enforces the
`authapp`/`authsigoption` script variables, so **an admin must grant these options before the
tools work**; the server never writes `APPLICATIONAUTH`. Privileged actions additionally
require the real IBM permission, so a kit grant can never substitute for `Apply Configuration
Changes` or `Manage Admin Mode`. Scripts also carry their own permission check, because the
handler's check fails open if the signature option row is missing.

### Changed

- `maximo_reload_cache` now prefers the permissioned `MCPUTILS.CACHE` utility. The old
  auto-deployed `MXKIT.RELOADCACHE` helper was **ungated** (invokable by any authenticated
  Maximo user) and is deprecated: it remains only as a fallback for instances that have not run
  setup, is flagged in the response, and is removed by `uninstall`. A permission denial on the
  new path no longer silently falls back to the ungated helper.
- Build now copies runtime `.py` assets into `dist` (`npm run copy:assets`).

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
