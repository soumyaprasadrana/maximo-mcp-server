# Changelog

All notable changes to `@soumyaprasadrana/maximo-mcp-server` are documented here.

## 2.1.0 -- 2026-11-07

Production hardening and the Maximo capabilities agents were missing: real workflow routing,
next-status validation, field lookups for every domain kind, group-by aggregation, BIRT reports,
integration errors and the Maximo server log, attachment upload, and limits. Every Maximo call in
this list was verified against a live Maximo first.

### Security -- the API key never leaves the configured Maximo

`os_query_builder` accepted any `basePath`, and the client used any absolute URL as is, so a
prompt-injected `basePath: "https://other.host/x"` made the working set send the apikey to that
host -- also on `--readonly`. Affects 2.0.0 and earlier.

- `MaximoClient.resolveUrl` now guards EVERY request: an absolute URL on the configured origin is
  used as is; one on another origin whose path is under the context root is a Maximo self-link
  (Maximo behind a proxy can encode another host or scheme into hrefs) and is REBASED onto the
  configured origin; anything else is refused (`HOST_NOT_ALLOWED`, `URL_NOT_ALLOWED`).
- `basePath` only picks between `/api/os` (default) and `/oslc/os`.
- API calls no longer follow redirects (fetch would replay the custom `apikey` header to wherever a
  3xx points). Raw downloads follow redirects by hand: on the same host with credentials, to
  another host (e.g. signed object-storage URLs) without them. Every raw call has a timeout.

### Changed -- truthful authentication errors

- A redirect from an API call is reported as `AUTH_REDIRECT` with its target. On MAS that is the
  login page: API keys work on `/api/...` while `/oslc/...` redirects API-key callers (verified on
  MAS); the message says so. Before: `UNAUTHORIZED` / `INVALID_JSON`.
- 401/403 keep Maximo's own reason and message (e.g. `BMXAA9549E - The API key token is invalid`,
  `BMXAA7901E`) instead of a bare "Maximo returned 401".
- Tool hints use `/api/whoami`; `/oslc/whoami` does not work for API keys on MAS.

### Changed -- workflow tools follow Maximo's workflow model

Verified live with test processes (START -> TASK -> STOP, and one with an INPUT node):

- `maximo_get_workflow_assignments` returns only OPEN assignments by default (`assignstatus
  ACTIVE`; `status: "ALL"` for none), each with `assignmentId`, task, assignee, owning record
  (`owner.table`, `owner.id`, `owner.description`) and its route `choices` with `onAccept` /
  `onReject` (from the `wfaction` child). Fixed: completed assignments were listed as pending,
  `ownertable` (an MBO name) was used as an object structure name, and the handler defaulted to
  `WFASSIGNMENT` while the schema said `MXAPIWFASSIGNMENT`. New filter `ownerId`;
  `includeAllowedActions` is deprecated and ignored (choices are always returned). Part of
  `--readonly` now.
- **New `maximo_complete_workflow_assignment`** -- routes an assignment like the Inbox:
  `accepted=true` positive route, `false` negative, with memo
  (`wsmethod:completeAssignment`). Plan first, then `confirm: true`.
- **New `maximo_start_workflow`** -- `action=workflow:<PROCESS>` after checking the process is
  active and for the record's object; returns the assignments the start created.
- Input nodes: when the next node asks for a choice, Maximo keeps that choice in an interactive
  login session; an API-key call to the returned location is refused (`oslc#invlaidwfinstid`) and
  the session cookie alone is not authenticated (BMXAA0021E). Reported as `input_node_reached` with
  the choices -- the assignment stays ACTIVE -- instead of as success.
- `maximo_send_workflow_response` stays for wsmethod actions on the owning record; its made-up
  "common action names" are gone from the description.

### Changed -- status changes are checked against Maximo's next-status list

`maximo_plan_status_change` only checked that a status action existed. It now also reads
`getlist~status` on the record -- transition-aware, verified: a closed or cancelled work order
returns none, COMP returns CLOSE/WORKCOMPLETE -- returns `valid_next_statuses`, and answers BLOCKED
for a target outside it. `maximo_change_status` refuses such a target with `invalid_target_status`
before sending anything. If the list cannot be read, Maximo decides as before.

### Added -- Maximo insight tools (all read-only, all on `--readonly`)

- **`maximo_lookup_values`** -- the values Maximo's lookup offers for one field
  (`getlist~<attr>` on a record, or on `newmbo` for a new one with `setupdata` context). Works for
  TABLE domains (assetnum, location, worktype, crew, failure code...) which metadata could not list,
  as well as synonym/ALN domains; on an existing record `status` gives the valid next statuses.
  `search` is a LIKE filter (`oslc.searchTerms` does not apply to getlist -- verified). A lookup
  Maximo cannot run returns its reason verbatim (e.g. BMXAA4107E).
- **`maximo_aggregate`** -- GROUP BY with `count`, `sum`, `avg`, `min`, `max` computed by Maximo
  (`gbcols` / `gbsortby`, verified: ~110-350 ms on 67k work orders), filtered with `where` first.
  Filtering on an aggregate (HAVING, `gbfilter`) is not supported by Maximo (BMXAA9757E). The
  `os_query_builder` note "aggregation not supported" now points here.
- **`maximo_list_reports` / `maximo_run_report`** -- BIRT through REST (`action=listreports` /
  `genreport`); the report (PDF by default) comes back as an embedded resource. Verified:
  `wotrack.rptdesign` for one work order -> PDF in ~11 s. Size cap `MCP_MAX_REPORT_MB` / `--max-report-mb` (10).
- **`maximo_integration_errors`** -- Message Reprocessing (`MXAPIMSGREPROC`) and Message Tracking
  (`MXAPIMSGTRACK`): per-interface/status counts plus the latest rows with their error text.
- **`maximo_read_server_log`** -- the tail of Maximo's own Liberty `messages.log`
  (`/api/service/logging?action=wsmethod:streamLog`, needs the STREAMLOG option of LOGGING) with
  `minLevel`, `contains`, `sinceMinutes`; stack traces stay together. streamLog sends the WHOLE
  log (18 MB in 3.4 s on a dev box), so the tail is kept in a bounded ring buffer and the scan is
  capped (`MCP_SERVER_LOG_SCAN_MB` / `--server-log-scan-mb`, 64). **Opt-in** with `MCP_ENABLE_SERVER_LOGS=true`
  (`--enable-server-logs`), because the log holds other users' data.

### Added -- `ws_add_attachment`

Attaches a file (text or base64) to a record of a working set (`POST <os>/<id>/doclinks`, document
folder `docType`, default Attachments). Not staged -- Maximo stores it at once -- so it is plan
first, then `confirm: true`. Verified: upload, list, then delete on a test work order.

### Changed -- limits and diagnostics

- `mcp_server_status` is registered on every server (an agent needs it to know whether the server
  is healthy and what it withholds; it contains no secrets). `mcp_read_logs` still needs
  `--dev-mode` or `--readonly`.
- Per-caller identity (`MCP_CALLER_APIKEY`) withholds `mcp_read_logs`, `ctx_list` and
  `maximo_read_server_log` in `toolRestrictions.ts` itself,
  reported as `callerIdentityWithheld` in `mcp_server_status`. Opt-in tools are reported as
  `optInWithheld`.
- `MCP_MAX_PAGE_SIZE` / `--max-page-size` (default 1000): a larger `os_query_builder` pageSize is clamped, with a
  warning. `mcp_read_logs` returns at most 5000 lines (`lines: 0` used to read whole files).
  Attachments over `MCP_MAX_ATTACHMENT_MB` / `--max-attachment-mb` (25) are refused before they are buffered.
  `MCP_MAX_CONCURRENT_TOOL_CALLS` / `--max-concurrent-tool-calls` (default 0 = unlimited) answers `server_busy` past the limit.
- `maximo_sql_query` sends the SQL in the POST body instead of the URL, so it stays out of
  Maximo and proxy access logs (the copilot script already read the body -- no reprovisioning).
- `os_query_builder` `savedQuery`: the description was wrong -- the saved query is ANDed with
  `where` (verified: CREATEDLOCALLY 21 rows, with `status=WAPPR` 15), the name is case-sensitive
  (lowercase `savedquery` is silently ignored and returns everything), KPIs are `KPI:<name>`, and
  the names come from `queryCapability` in `maximo://os/{osName}` (now listed in
  `maximo_get_metadata`'s description).
- `maximo_change_status` no longer sends this host's clock as the status `date` when none is
  given; Maximo then applies its own current time. Found live: on a Maximo whose clock / DB timezone
  ran 5.5 h ahead of the MCP host, the old default was refused with "BMXAA4673E - The status change
  date cannot be earlier than the date of the last status change". An explicit `statusDate` is
  still sent as given.
- One-shot commands (`--setup-copilot`, `--copilot-status`, `--setup-oauth`, ...) print a failure
  on stderr with Maximo's reason; before, it went only to the log file and the command exited 1
  silently.

### Tests

New offline suite `npm run hardening_test` (30: same-host guard, basePath, page limit, log
parsing); `tool_reg_test` 155 (new tools, opt-in and caller-identity gating); all other suites
unchanged and passing. Live against a local Maximo through the release build: 41 checks over every
new and changed tool (workflow start/route on test work orders, lookups, group by, reports,
integration errors, server log, status validation, attachment upload and removal, basePath
refusal, page clamp, saved query + where), plus the on-demand (15), persistence (14), tool
restriction (11) and caller-identity (11) suites; truthful auth errors verified on MAS.

## 2.0.0 -- 2026-11-06

### Changed (breaking) -- one edition: every tool ships in the npm package

The premium/public split is gone. Until now the npm package was a separately built "public" cut
(1.4.x) with the configuration tools stubbed out, while the full server (1.5.0 - 1.7.x) was
available on request. 2.0.0 is a single build and a single version line: the package on npm
contains everything -- including the configuration tools (Configure Database status / apply /
discard, Admin Mode, system properties, read-only SQL, live cache reload, App Designer
presentation editing, the copilot utility setup) and async commits with `ws_commit_status`.

- `src/edition.ts` (`EDITION`, `isPremiumEdition`, `PREMIUM_ONLY_TOOLS`) is removed, along with
  every gate on it. `tools/maximo/premium.ts` is now `configurationTools.ts`
  (`registerConfigurationTools`); it still registers only outside `--readonly`, and the ten
  copilot-only tools only with `--copilot-mode` (see below).
- `build-public.js`, `npm run build:public` and `npm run publish:npm:public` are removed. Build
  with `node build.js` and publish `delivery/release` with `npm run publish:npm`.
- `OSWorkingSetEngine.shouldCommitAsync` no longer forces inline commits for the public build, so
  slow object structures (e.g. `DMMAXOBJECTCFG`) commit asynchronously everywhere, polled with
  `ws_commit_status`.
- The copilot one-shot commands (`--setup-copilot`, `--copilot-status`, `--uninstall-copilot`) and
  `MCP_COPILOT_AUTO_PROVISION` are no longer edition-gated.
- `build-cli-template.js` (only used by the public build) is removed. It had drifted from the
  inline CLI in `build.js`: the `--enable-script-get` flag added earlier in this release existed
  only in the template, so it never reached the shipped CLI. It is now in `build.js`.

### Removed (breaking) -- bundled local-embeddings dependencies

`@xenova/transformers` and `onnxruntime-node` are no longer dependencies. They pulled native
onnxruntime / sharp binaries whose install fails on some machines, and a dependency cannot be
opted out of. `onnxruntime-node` was not imported anywhere. `MCP_EMBEDDINGS_MODE=local` still
works for anyone who installs `@xenova/transformers` themselves (`npm install -g
@xenova/transformers` next to a global install); the library is now resolved at runtime, and
without it the server logs one clear install hint and falls back to keyword search, as before.
`MCP_EMBEDDINGS_MODE=openai` was never implemented and now says so in the log. Default `none` is
unchanged. `@modelcontextprotocol/inspector` moved to devDependencies (it was already stripped
from the release). `npm install` removed 51 packages.

### Changed -- `ws_remove` is part of the `--readonly` surface

An agent on a read-only server can now clean up its own working sets. `ws_remove` only frees
this server's in-memory session and never touches Maximo. Read-only is now 12 Maximo tools plus
the two diagnostics (13 Maximo tools with `MCP_ENABLE_SCRIPT_GET`).

Verified live against a real Maximo from the single release: normal mode registered 51 tools
including the configuration tools (before the copilot-only gate below; at release 44 with
`--dev-mode`, 53 with `--copilot-mode` as well); `--readonly` registers 14, including `ws_remove`, which
removed a loaded working set (a later read returns `ws_not_found`); `MCP_EMBEDDINGS_MODE=local`
without the library logs the install hint and the server runs. `tool_reg_test` 110/110 at that point (127 at release): its
expected list now covers every registered tool (11 were only producing warnings before).

### Added -- working sets that survive a restart (`MCP_WS_PERSIST` / `--ws-persist`)

Working sets lived only in a per-process Map: a restart lost every loaded record and staged,
uncommitted change. With `MCP_WS_PERSIST=true` (off by default -- it writes business data to disk)
they are also kept in `<data-dir>/data/workingsets.db`, a SQLite file separate from `meta.db`. The
in-memory Map stays the hot path; the tool behaviour is unchanged.

- **Write-through at the tool boundary.** The engine records which working sets each tool call
  touched; after the call the tool layer calls `flush()`, which writes each one whose snapshot (or
  commit lock) changed, gzip'd, and only refreshes the stored expiry (at most every 30 s) for the
  rest. Doing it at the boundary covers every mutation path -- engine methods and the tools that
  call `OSWorkingSet` directly -- without instrumenting each mutator.
- **Read-through.** A working set that is not in memory (fresh process, or dropped after
  inactivity) is rebuilt on first access from `OSWorkingSet.toSnapshot()` /
  `OSWorkingSet.fromSnapshot()`. A new-record draft is the same object in `created` and `working`;
  the snapshot stores it as a reference so a `ws_update_draft` after a restore still reaches what
  the commit sends. Sets whose hrefs point at a different `MAXIMO_URL`, unknown snapshot versions
  and expired sets are not restored.
- **Crash-safe commits.** The commit lock is written before anything is sent (write-ahead). A
  working set restored while still marked as committing by a process that is gone refuses
  `ws_commit` with `commit_outcome_unknown` until `ws_discard`, so staged changes are never
  resent automatically. A reload does not clear the hold -- `ws_load` keeps staged changes, so a
  commit after it would resend them. If the write-ahead save itself fails (disk full,
  `SQLITE_BUSY`), the commit is refused with `persist_failed` and nothing is sent. Commit jobs are stored too: a finished job's
  result is pollable after a restart, and one that was running when the server stopped is reported
  `interrupted` (new `CommitJobStatus`).
- TTL: `MCP_WS_TTL_MINUTES` (default 15, unchanged); expired rows are swept with the existing
  eviction timer, whose interval is now `MCP_WS_SWEEP_SECONDS` / `--ws-sweep-seconds` (default
  60, clamped to 5..3600; `mcp_server_status` reports it as `workingSets.sweepSeconds`). `ws_remove` deletes the stored row. `mcp_server_status` reports `workingSets`
  (enabled, in memory, stored, interrupted commits).
- **Cleanup and disk space.** Expired working sets (and, after a 7-day grace, ones abandoned
  mid-commit) and commit jobs older than 24 h are deleted on the eviction timer and once at
  startup, so what expired while no server ran is gone before the first request. SQLite never
  shrinks a file on its own, so the store runs with `auto_vacuum=INCREMENTAL` (an older file is
  converted with one `VACUUM`) and returns free pages to the OS in bounded steps (about 16 MB per
  pass) after each sweep that deleted something and on every following tick until no free space
  is left, plus at least every 10 minutes; `journal_size_limit` and a TRUNCATE
  checkpoint keep the `-wal` file from staying at its peak. A 40 MB burst went back to 32 KB in
  three passes in the test suite.
- **Size cap.** `MCP_WS_PERSIST_MAX_MB` (default 64, serialized) bounds both the file and the time
  a save holds the event loop (JSON + gzip are synchronous). A bigger working set stays in memory
  only, any older stored copy of it is deleted (restoring it would bring back stale staged
  changes), and `mcp_server_status` counts it.
- If `MCP_WS_PERSIST` is off but `workingsets.db` exists, the server logs a warning at startup:
  that business data would otherwise sit on disk unread and never expire.
- Not in scope: binding a working set to the calling client (today, as before, any caller that has
  an id can use it), and sharing working sets across several server nodes -- one SQLite file per
  data directory gives restart survival; scale-out still needs sticky routing.

New offline suite `npm run wspersist_test` (57 checks). Live against the local Maximo through real
server restarts (14 checks): a change staged on one server process was restored by the next,
previewed and committed to Maximo from the restored working set, then reverted; a removed working
set stayed gone; with the flag off nothing is restored. The live tool regression suite (15 checks)
passes with persistence on and off.

### Changed (breaking) -- automation-script tools need `MCP_COPILOT_MODE`; `MCP_DISABLED_TOOLS`

Nine tools work by running an automation script inside Maximo: `maximo_copilot_setup` uploads the
`MCPUTILS.*` Jython utilities (through `MXAPIAUTOSCRIPT`) and adds their signature options to
CONFIGUR / PROPMAINT; `maximo_dbconfig_status`, `maximo_dbconfig_apply_status`,
`maximo_dbconfig_discard`, `maximo_dbconfig_apply`, `maximo_admin_mode`, `maximo_sql_query` and
`maximo_system_property` then call `/api/script/MCPUTILS.<NAME>`; `maximo_reload_cache` calls
`MCPUTILS.CACHE` or deploys its own `MXKIT.RELOADCACHE`. They reach SQL, system properties, Admin
Mode and Configure Database -- a developer surface -- so they are now registered **only when
`MCP_COPILOT_MODE=true`** (`--copilot-mode`). Before, they were registered on every non-readonly
server, and `maximo_copilot_setup` refused to provision without copilot mode anyway.
`maximo_appdesigner_edit` is copilot-only too: it is not script-backed, but it writes through
`DMMAXAPPS`, a Migration Manager object structure only copilot mode exposes, so outside copilot
mode it could only fail. Ten tools in all (`COPILOT_ONLY_TOOLS`).

- **Breaking for**: a server that used these tools without `--copilot-mode`. Add the flag.
- **New `MCP_DISABLED_TOOLS` / `--disabled-tools`**: a comma-separated deny list applied to every
  tool (Maximo, dev and ctx), in every mode. Exact names or a `prefix*`, case ignored. A disabled
  tool is never registered, so it is absent from `tools/list` and a call to it is an unknown tool.
  An entry that matches no tool is logged as a warning at startup -- a typo would otherwise
  silently leave exposed what it meant to hide.
- One registration filter (`src/tools/toolRestrictions.ts`) installed on the server before any
  tool registers; readonly filtering is unchanged and still happens first.
- `mcp_server_status` reports `toolRestrictions`: copilot mode, the copilot-only tools withheld,
  the deny-list entries, the tools they withheld and any entry that matched nothing.
- `maximo_invoke_automation_script` refuses a script that backs a withheld tool
  (`MCPUTILS.SQLQUERY`, `.SYSPROP`, `.DBCONFIG`, `.CACHE`, `.BOOTSTRAP`, `MXKIT.RELOADCACHE`,
  any case) with `script_not_allowed`, so the generic tool cannot reach what the gate hides.
- `tool_reg_test` 127 checks: the full surface with copilot mode, the ten withheld without it,
  and the deny list (exact, prefix, case, no collateral, unmatched entry reported).

### Added -- per-caller Maximo identity over HTTP (`MCP_CALLER_APIKEY` / `--caller-apikey`)

Until now every Maximo call used the server's own `MAXIMO_API_KEY`, so everyone behind one HTTP
server acted as one Maximo user. With `MCP_CALLER_APIKEY=true`, an HTTP request that carries
`x-maximo-apikey` runs as that caller: `MaximoClient` sends the caller's key for every call the
request makes (including an async commit that finishes after the response), so Maximo applies
that user's own security groups, data restrictions and esig rules. A request without the header
keeps the server's identity. Off by default; stdio is unaffected.

- The identity rides an `AsyncLocalStorage` (`src/maximo/callerIdentity.ts`); only a 16-hex
  SHA-256 tag of the key is ever stored or compared.
- **Working sets are private to their creator**: a set created by caller A answers
  `ws_not_found` to caller B and to the server identity (its records were read with A's
  permissions), and vice versa. The owner tag is persisted with `--ws-persist` snapshots; older
  snapshots restore as server-owned.
- **Metadata stays server-level**: on-demand fetches run with `MAXIMO_API_KEY` even inside a
  caller's request, because the local object-structure index is shared.
- A configured cookie is never sent together with a caller's key.
- Permission-aware reads follow the caller too: `maximo://os/search` filters object structures by
  the caller's own app permissions, and the working-set permission checks use the caller's grants.
- Verified live over HTTP against a real Maximo (11 checks): no header -> server identity; a valid
  caller key -> that user; a key Maximo rejects is refused (the server key is not used as a
  fallback); metadata still loads; working sets are invisible across identities; the port is not
  reachable from the LAN with `MCP_SERVER_HOST=127.0.0.1`.
- `ctx_*` sessions and the server log are not per-user: front ends that mix users should disable
  `ctx_list` and `mcp_read_logs`.
- New `MCP_SERVER_HOST` / `--host`: bind address for the HTTP transport. Unset keeps listening on
  all interfaces (containers need that); `127.0.0.1` when only a co-located proxy may connect.
- New offline suite `npm run identity_test` (18 checks): credentials per request, identity across
  awaits and timers, `runAsService`, no leak outside the request, working-set isolation in every
  direction (including commit), flag off = unchanged, owner tag in snapshots.

### Added -- on-demand metadata (`MCP_RECONCILE_LAZY` / `--reconcile-lazy`)

The startup sync downloads every object structure's metadata before any tool can run -- on a large
Maximo, minutes of `metadata_sync_in_progress`. On-demand mode (off by default; eager mode is
unchanged) skips it. Before each Maximo tool call, the guard in `tools/maximo/index.ts` works out
what the call needs -- `osName`, the working set id's OS, `childCollection.responseOs`, the
`maximo://` URI, dot-notation `where` objects -- and `metadataengine/onDemand.ts` fetches only what
is missing or past its TTL, through the same loaders and into the same tables the full sync uses.
Every reader (query builder, validator, search, permission check) is untouched.

- Units: the catalog (`/api/apimeta`), one OS (apimeta detail, JSON schema and subschemas in
  parallel, its member objects from `MAXMCPMETADATA`), single objects.
- Freshness: `MCP_RECONCILE_LAZY_TTL` (default 86400 s), `MCP_RECONCILE_LAZY_CATALOG_TTL` (3600),
  `MCP_RECONCILE_LAZY_NEGATIVE_TTL` (300) for not-found and failed fetches. New `meta_cache` table
  (schema v5) records when each entry was fetched and when it expires.
- Concurrent calls for the same OS share one fetch. A failed refresh keeps serving the previously
  fetched data and backs off; with nothing cached the call fails with `metadata_fetch_failed`,
  never an empty success.
- Data from an earlier full sync counts as fetched at that sync's time, so an existing data
  directory switches with no refetch. On-demand mode never writes
  `last_success_initial_reconcile`, so switching back to eager mode still runs the full sync.
- `--force-reconcile` and the weekly cron invalidate the cache instead of bulk-reloading.
  `MCP_RECONCILE_SYNC` and `MCP_BG_SYNC_WORKER` are ignored in this mode.
- `mcp_server_status` reports `sync.metadataMode` and `sync.onDemand` (TTLs, script contract,
  cache counts, fetches, hits, failures).
- Known limit: MCP resources (`resources/read`) are not routed through the guard, so in on-demand
  mode they only see object structures a tool has already loaded.

Measured on a local Maximo (383 object structures), empty data directory: server ready in 3.8 s;
first use of MXAPIWODETAIL 9.2 s, repeat 7 ms; a second OS about 4 s; the DB held 2 schemas and 30
objects afterwards. With the original script deployed: first use 16 s (whole MBO payload, once),
later object structures under 1 s.

### Fixed -- `MAXMCPMETADATA` failed on any database whose schema is not `maximo`

Two queries read `maximo.MAXINTOBJDETAIL` while every other query in the script is unqualified,
so the script failed on SQL Server (`Invalid object name 'maximo.MAXINTOBJDETAIL'`) and on any
instance whose schema owner is not `maximo` -- every tool then answered
`metadata_sync_in_progress` or `metadata_fetch_failed`. Present in v1 as well. Both queries are
unqualified now; verified on SQL Server (MAS) and on the local DB2 instance. **Redeploy the
script** on affected instances.

### Changed -- `MAXMCPMETADATA` v2 (optional parameters, prepared statements)

`src/maximo/autoscripts/MAXMCPMETADATA.py` declares `MCP_METADATA_CONTRACT = 2` and accepts
`mode=catalog` (object structure -> member objects, 22 KB / 0.3 s), `mode=os&os=A,B` (one or more
object structures, 839 KB / 7.4 s for MXAPIWODETAIL) and `mode=object&objects=X,Y`. With no
parameters the output is byte-for-byte the original payload plus a `_meta` block -- verified
identical against the deployed v1 on 383 object structures / 487 objects. Names are checked
against `[A-Z0-9_]`, 1-30 characters, and bound as PreparedStatement parameters (the script runs on
the system user's connection); injection attempts are refused with an `error` field. The server
detects the contract by reading the script source from MXAPIAUTOSCRIPT, not by calling it, because
the original script ignores parameters and would return the full payload. Redeploying the script
is optional: everything works with the original one.

### Fixed -- metadata search-index and catalog bugs in the regular sync

- `objects_fts` was always empty: the insert listed 5 columns with 4 placeholders, and the error
  was swallowed.
- FTS rows were duplicated on every sync: FTS5 tables have no primary key, so
  `INSERT OR REPLACE` appended instead of replacing (571 object-structure index rows for 383 object
  structures on the test instance). The full sync now rebuilds the indexes; per-entity reloads
  delete the entity's old rows first.
- Object structures, objects and attributes removed in Maximo were never removed locally (571
  object structures in the DB against 383 live). The full sync now prunes them -- except on an
  empty catalog, which is treated as a failed fetch rather than wiping the DB.
- The object-structure search index stored the primary object name in its `description` column.
- Reloading metadata reset each relationship's learned pheromone / usage counters.
- `os_query_builder` called a `validateOSLC` method that does not exist (dead code, removed), and
  `reconcileManual`'s rowid-based FTS cleanup -- which would now delete freshly written rows -- is
  removed.
- `attributes(object_name)` and `relationships(parent_object)` are indexed, and SQLite waits up to
  5 s for a lock (`busy_timeout`) instead of failing with SQLITE_BUSY when the sync worker writes.

New offline suite `npm run ondemand_test` (45 checks: the loader fixes and the on-demand contract,
against a throwaway DB and a fake client). Live against the local Maximo: 15/15 in on-demand mode
with the v2 script and 15/15 with the original script.

### Security -- `maximo_get_url` checks the path as the servlet container maps it

The script-path refusal tested the raw URL path, so `/api/%73cript/X`, `/api/script;x=1/X`,
`//api/script/X` or `/api/script%2FX` would pass it, and a container that decodes and strips
`;params` before mapping would run the script through a read-only tool. The path is now
decoded per segment, `;params` stripped and slashes collapsed before the context-root and
script checks; `.` / `..` segments and undecodable paths are refused. Affects 1.4.16.

### Already on npm: the work below shipped as public 1.4.16 (2026-11-02) and is part of 2.0.0

### Added -- `maximo_get_url`: read-only GET for any Maximo URL (in `--readonly`)

A generic escape hatch for Maximo endpoints no dedicated tool covers (`/oslc/whoami`, a child
collection href, `/api/error/messages/<code>`, ...). `url` is a path on the configured Maximo
(context root added; a path that already carries it is accepted) or a full URL on the same host;
`params` adds query parameters, `headers` adds request headers, `maxBytes` caps the body
(default 200000, max 2000000). JSON is returned parsed; larger bodies are truncated and binary
bodies omitted. The readonly surface was then 11 Maximo tools (12 in 2.0.0 with `ws_remove`).

It has to keep `--readonly` truthful, and a plain GET in Maximo is not always a read, so:

- **GET only** -- no method, body or `X-Method-Override`.
- **Same host only** -- the client sends the apikey with every request, so anything not on the
  configured `MAXIMO_URL` is refused (including `user@host` URL tricks and `..` out of the
  context root). Redirects are not followed (new `RequestOptions.noRedirect`), so a 3xx cannot
  replay the key elsewhere.
- **`action=` refused** (any case, in the URL or `params`): it invokes a Maximo action.
  **`/api/script/*` and `/oslc/script/*` refused**: they run automation scripts. Both are routed
  to `maximo_invoke_action` / `maximo_invoke_automation_script`, which are write tools. This is
  enforced in every mode, not only `--readonly`.
- **Credential headers refused**: `apikey`, `authorization`, `proxy-authorization`, `cookie`,
  `maxauth`, `x-method-override`, `host`, and hop-by-hop headers.

Client plumbing: `MaximoClient.getPassthrough()` returns status, a few response headers and a
streamed, capped body (a large download is never pulled fully into memory).

### Changed -- `maximo_invoke_automation_script` moved out of the premium-only set

Moved out of the premium-only set (`PREMIUM_ONLY_TOOLS`). It is a **write** tool -- a script runs
immediately, with no preview, and can change data even on GET -- so it is hidden under `--readonly`
by default (see `MCP_ENABLE_SCRIPT_GET` below for the opt-in). The tool and its `invokeScript()` helper now live in
`tools/maximo/automationScriptTools.ts`; the premium-only `maximo_reload_cache` stays in
`scriptTools.ts` and imports the helper. (In 2.0.0 the split itself is gone -- see above.)

Live-verified through a real MCP client against both editions: public `--readonly` lists
`maximo_get_url` and no script tool; public normal lists both `maximo_get_url` and
`maximo_invoke_automation_script` and no `maximo_reload_cache`; premium lists all three.
`maximo_get_url` returned `/oslc/whoami` and a paged `mxapiwo` query, passed a Maximo 404 error
body through verbatim, reported a 302 without following it, and truncated at `maxBytes`; every
refusal case above returned its own reason code. `maximo_invoke_automation_script` against a
non-existent script returned Maximo's `BMXAA4216E` (no script was executed).

### Security -- the apikey is no longer put in the URL query string

`MaximoClient.getRaw()` used to copy the apikey into the query string (`?apikey=...`) as well as
the `apikey` header. A key in a URL ends up in Maximo, proxy and load-balancer access logs. That
path serves automation-script GETs (`maximo_invoke_automation_script`, now reachable from the
public edition) and attachment downloads. Removed: the key travels in the header only. Verified
live before changing it -- a script GET (the mandatory `MAXMCPMETADATA` script) returns 200
header-only, and a real attachment round trip (upload, then download) returns the file header-only.
The debug-level request logging also printed the full header set including the key and cookies;
`apikey`, `cookie`, `authorization`, `maxauth` and `esigauth` values are now redacted there.
`postBinary` already used the header only.

### Added -- `MCP_ENABLE_SCRIPT_GET` / `--enable-script-get`: opt-in script GET in read-only mode

By default `--readonly` still hides `maximo_invoke_automation_script`, because a script can change
data on a GET. With this flag (and `--readonly`) the tool is registered in a **GET-only** form --
its schema has only `scriptName` and `params`, no `httpMethod` and no `body`, and the handler
ignores both even if a client sends them (verified: a smuggled POST + body ran as a GET). The
operator is declaring that the scripts reachable by the API user are safe for a read-only server.
No effect without `--readonly`. `maximo_get_url` still refuses script paths in every mode and
points to this tool. `mcp_server_status` now lists the flag. The self-test checks that the flag
adds exactly that one tool with no `body` / `httpMethod`.

### Changed -- count-only loads no longer report `hasMore`

`ws_load` on a `count:true` query returns no rows by design, but `meta.hasMore` was set because
the total exceeded the (zero) rows. It is now omitted for count queries. Verified live:
`count:true` -> `meta: { count: 0, totalCount: 66909 }`.

### Docs, rewritten -- `MC_TOOLS_USAGE_GUIDELINES.md`

Rewritten from scratch as an operating guide for an agent: what each deployment mode provides, an
intent-to-tool router, the response envelope and where to stop for the user, an error-reason
playbook, working-set and ctx lifecycle, step-by-step recipes for every workflow (read, count,
page, create, update, child rows, status with e-signature, workflow, actions, import, attachments,
scripts, raw URL, audit), the query reference, and rules R1-R22. It also fixes errors in the old
guide: the create flow named a `ws_add_record` tool that does not exist (it is `ws_update_draft`
with `temp_id`), and rule R7 named `ws_send_workflow_response` (it is
`maximo_send_workflow_response`).

`schemas/tool_schemas_loose.json` and `schemas/tool_schemas_strict.json` were regenerated
(`npm run dump_schemas`).

### Docs

`docs-site/docs/tools/index.md` was missing the allowed-actions, paging, import and generic-URL
tools and is realigned with the public surface; `docs-site` configuration documents the readonly
surface, `MCP_ENABLE_SCRIPT_GET` and `MAXIMO_ESIG_AUTH`. `VERSIONS.md` (and its docs-site copy) still said published 1.4.3
and current 1.7.1; corrected (it now reads published 1.4.16 / next 2.0.0).

## 1.7.13 -- 2026-10-15

### Added -- `maximo_import_file` and `maximo_import_file_status` (REST file import)

Maximo's REST file import (`POST /api/os/{os}?action=importfile`) is now a tool pair, both write-
gated (not registered under `--readonly`):

- **`maximo_import_file`** -- uploads a CSV (`filetype` FLAT, header row first) or XML document,
  passed inline as `content`, through an object structure. **`preview` defaults to true**:
  Maximo validates and returns `{totaldoc, validdoc, invaliddoc, warningmsg}` without writing;
  the caller shows that to the user and re-calls with `preview:false` to commit. Optional
  `delimiter` / `textQualifier` for CSV, and `async:true` (+ `name`) to queue a large load --
  the response then carries a `statusUrl` taken from Maximo's `Location` header.
- **`maximo_import_file_status`** -- polls that `statusUrl`. It refuses any URL not on the
  configured Maximo host, since the client sends the apikey with every request.

Identity comes from the apikey, so the documented `maxauth` header is not sent (verified: a
preview with only `apikey` succeeds). Client plumbing: `MaximoClient` gained `postText()` (raw,
non-JSON body, returns the `Location` header) and `RequestOptions.rawBody`; `OSClient` gained
`importFile()` / `getImportStatus()`. Content is inline only -- no server-side file path input,
which would let an agent upload arbitrary local files.

Live-verified on a real instance via MCP client against `MXAPIMETER`: default preview wrote
nothing; `preview:false` loaded 2 records (`validdoc:2`); `async:true` returned a `statusUrl`
that polled `mxapifileimportqueue` progress; an unknown object structure surfaced Maximo's
`BMXAA1281E` verbatim. Test records were deleted afterwards.

### Added -- `count` and `ignorecollectionref` on `os_query_builder`

Two optional boolean query flags, both off unless set:

- **`count`** -> `count=1`. Maximo runs a bare `SELECT COUNT(*)` for the query and responds with
  only `{"totalCount": N}` and no records -- the cheapest way to get a total. `collectioncount`
  is unchanged and still returns the page of rows plus `responseInfo.totalCount`.
- **`ignorecollectionref`** -> `ignorecollectionref=1`. Omits the `*_collectionref` child
  collection hrefs from every returned record, shrinking responses.

`MaximoClient.parseResponse()` now recognises the `{"totalCount": N}`-only body as a count rather
than a record: `items` is `[]` and `count` is `N`. Before this, such a body would have been
returned as a single bogus item.

## 1.7.12 -- 2026-09-12

### Added -- Electronic Signature (esig) support on `maximo_change_status`

Maximo's SIGOPTION mechanism lets customers require an electronic signature (a re-entry of the
signed-in user's password, plus a reason) before certain actions execute -- a native, per-action,
customer-configurable requirement this server previously had no way to see, satisfy, or even
surface: an esig-protected status change simply failed with an opaque, generic error.

`maximo_change_status` now always sends `checkesig=1` on invocation, asking Maximo to enforce
whatever esig requirement is configured for the detected action. Two new optional inputs let a
caller complete the flow in the same two-call shape as the rest of this tool:

- **`esigAuth`** -- `base64(password)` for the currently-signed-in Maximo user (the identity
  behind this connection's own apikey). **Not** `base64(userid:password)` -- confirmed live that
  including the userid makes Maximo reject an otherwise-correct password with `BMXAA3840E`
  ("signature not valid"); Maximo already knows who is signed in and validates the signature
  against that identity implicitly.
- **`esigReason`** -- free-text reason recorded against the signature.

If esig is required and `esigAuth` is missing or wrong, the call fails with `op_success:false`
and `error.reason: "esig_required"` (matched on Maximo's `BMXAA9766E` reasonCode -- never on the
message text, which is locale-translated). The intended flow: call `maximo_change_status`
normally; on `esig_required`, prompt the user for their Electronic Signature key and a reason;
base64-encode the password alone; call it again with the same parameters plus
`esigAuth`/`esigReason`.

`OSClient.invokeAllowedAction()` gained a shared `EsigInvokeOptions` parameter
(`checkEsig`/`esigAuth`/`esigReason`) so the same support can be extended to
`maximo_invoke_action` / `maximo_send_workflow_response` later without changing the underlying
mechanism -- scoped to `maximo_change_status` only for now, per the immediate ask.

Also: `maximo_change_status` now always sends a `date` to Maximo -- previously omitted entirely
when the caller didn't pass `statusDate`, leaving Maximo to default it server-side. It now
defaults client-side to the current time in UTC (`new Date().toISOString()`, always
`Z`-suffixed) when `statusDate` is omitted, so behavior is explicit and independent of the
server process's local timezone.

Live-verified end-to-end against a real Maximo instance, including a discovery this instance
actually has esig configured on `changeWOStatus`:
- No `esigAuth` -> `op_success:false`, `error.reason:"esig_required"`, `maximo_reason_code:"BMXAA9766E"`.
- `esigAuth` as `base64(userid:password)` (tried first, with a real, correct password) ->
  still rejected with `BMXAA3840E` -- the userid in the encoded value is itself the problem.
- `esigAuth` as `base64(password)` alone, correct password, no `statusDate` passed -> full
  round trip succeeded: `WAPPR -> APPR -> WAPPR` on the same record, both legs `204`, `date`
  observed in the tool's response as a current UTC timestamp each time.

### Added -- server-managed Electronic Signature for multi-tenant deployments (`MAXIMO_ESIG_AUTH`)

The design above assumes whoever is calling `maximo_change_status` knows the signing user's own
Maximo password. That's fine for a single admin using their own credential, but breaks down for
the actual deployment shape this server targets: one MCP instance, one shared `MAXIMO_API_KEY` /
service account, and many chat-agent end users -- none of whom have ever known, and never should
know, that service account's password.

New optional env var **`MAXIMO_ESIG_AUTH`** (base64 of the PASSWORD ONLY for the user behind
`MAXIMO_API_KEY` -- same format as `esigAuth`, see above): when set, `maximo_change_status` fills
it in automatically whenever a caller omits `esigAuth`, so end users are only ever asked for a
*reason*, never a credential. A caller-supplied `esigAuth` always takes precedence, so an
individual signing as themselves still works unchanged. `runtimeFlags.ts` gained
`isEsigAuthConfigured()` / `getConfiguredEsigAuth()`; the tool's own description text changes at
registration time depending on whether this is set, so an agent reading the schema is told the
right thing to ask the user for.

This also changes what "wrong signature" should mean. `BMXAA3840E` (signature supplied but
rejected) now branches on whether the *server's* configured credential was the one used: if so,
it's surfaced as a distinct `error.reason: "esig_invalid_server_credential"` with an explicit
instruction not to ask the current end user for a password -- they have none to give, and asking
would be a dead end. A caller-supplied `esigAuth` that's simply wrong still falls through to the
generic failure path, where re-prompting the same caller is the right move.

Live-verified all three shapes end-to-end on the same record:
- No server config, no caller `esigAuth` -> `esig_required` (unchanged from above).
- Server config set to the correct password, caller passes **no** `esigAuth` at all -> full
  `WAPPR -> APPR -> WAPPR` round trip succeeded automatically, `204` both legs.
- Server config set to a wrong value -> `esig_invalid_server_credential`, explicitly not asking
  for the end user's own password.

**Note:** `BMXAA3840E` from a caller-supplied (not server-default) `esigAuth` still falls through
to the generic `change_status_failed` path rather than a dedicated reason code -- a reasonable
fast-follow if a caller needs to distinguish "never signed" from "signed wrong" in that case too.

## 1.7.10 -- 2026-09-12

### Fixed -- `changeStatus` false-negative: "not in the allowed actions" even though Maximo allows it

Found live testing 1.7.9's fix against a second work order (`MXAPIWODETAIL/_QkVERk9SRC8yMDAz`,
WO 2003): passing `actionName: "changeStatus"` to `maximo_change_status` /
`maximo_plan_status_change` failed with `'changeStatus' is not in the allowed actions for
MXAPIWODETAIL/...` -- even though invoking `wsmethod:changeStatus` directly against the same
record succeeds. Root cause: `changeStatus` is Maximo's base/global status-change wsmethod,
present and invokable on every status-enabled MBO regardless of object structure, but Maximo's
own `allowedactions` discovery response does **not** always enumerate it -- that endpoint
reflects registered/documented per-object-structure actions (e.g. `changeWOStatus`, which IS
listed), not base methods inherited generically. `findAllowedAction()`'s membership check against
that (correctly parsed, since 1.7.8) but incomplete list treated "Maximo's discovery didn't
mention it" as "Maximo doesn't allow it" -- a false negative, not a permissions problem.

Fixed with a narrow, named exception in the one shared lookup
(`findAllowedAction` in `maximo/utils/allowedActions.ts`): when `changeStatus` (or
`wsmethod:changeStatus`) is asked for by name and isn't in the discovered list, it now returns a
synthesized action descriptor for it instead of `undefined`, so the gate no longer blocks the one
action known to be safe and global independent of what discovery reports. Every caller
(`maximo_change_status`, `maximo_plan_status_change`, `maximo_invoke_action`) shares this function,
so all three pick up the exception automatically -- no per-tool changes needed.

Live-verified end-to-end through the actual MCP tool on the exact record the failure was found on:
WO 2003 moved `WAPPR -> APPR` via `maximo_change_status` with `actionName: "changeStatus"`,
confirmed by re-fetch. `changeWOStatus` (auto-detected, no override) is unaffected and continues
to work as fixed in 1.7.9 -- this exception only applies when `changeStatus` is explicitly
requested by name.

## 1.7.9 -- 2026-09-12

### Fixed -- every write-type allowed-action invocation ("this.mboSet is null") -- `maximo_change_status`, `maximo_invoke_action`, `maximo_send_workflow_response`

1.7.8 fixed `allowedactions` parsing so the gate correctly reported a transition as `ALLOWED`, but
actually executing it still failed. Live-verified root cause in `OSClient.invokeAllowedAction()`:
the call site was `this.client.post(url, params, { "X-Method-Override": "PATCH" })`, while
`MaximoClient.post()`'s signature is `(path, body, params, headers, opts)`. The header object
landed in the 3rd (`params`, i.e. extra query string) slot, not the 4th (`headers`) slot -- so
instead of a real `X-Method-Override: PATCH` header, the request carried a useless
`?X-Method-Override=PATCH` query string and **no override header at all**. Maximo's action
framework depends on that header to build the Mbo context for a wsmethod/system action invoked
via POST; without it every such call failed server-side with an opaque
`Cannot invoke "psdi.mbo.MboSet.getMboServer()" because "this.mboSet" is null` -- indistinguishable
from a real Maximo bug unless you knew what request was actually on the wire.

This affected **every POST-type action invocation**, not just status changes: `maximo_change_status`,
`maximo_invoke_action`, and `maximo_send_workflow_response` all route through this one method.
GET-type actions (`islocked`, `sigopgranted`, etc.) were unaffected -- they use a different branch.

Fixed by passing query params and headers in their correct positional slots. Live-verified against
a real Maximo instance end-to-end through the actual MCP tools (not just a raw request): a real
work order was moved `WAPPR -> APPR` via `maximo_change_status` (previously NPE'd every time),
confirmed via a fresh record fetch, then moved back `APPR -> WAPPR` to restore its original state.
No action-name changes were needed -- the auto-detected action (e.g. `changeWOStatus` for
MXAPIWO/MXAPIWODETAIL) was correct all along; this was purely a request-construction bug.

**Upgrade note:** if you took 1.7.8 (or public 1.4.10), `maximo_change_status`, `maximo_invoke_action`,
and `maximo_send_workflow_response` fail on every POST-type action with the `this.mboSet is null`
error until this release. The read-only discovery tools (`maximo_get_allowed_actions`,
`ws_get_allowed_actions`, `maximo_plan_status_change`) were unaffected -- they never invoke anything.

## 1.7.8 -- 2026-09-11

### Fixed -- `allowedactions` was parsed as the wrong shape, so `maximo_change_status` and `maximo_send_workflow_response` rejected every action, always

Found live while investigating a generic action-invocation design: Maximo returns `allowedactions`
as an OBJECT keyed by action key (`{"wsmethod:changeWOStatus": {...}, "discardedit": {...}, ...}`),
identically in lean and non-lean mode -- not the array of `{action: "..."}` entries the parser in
both `statusTools.ts` and `workflowTools.ts` assumed. `Array.isArray(raw)` on that object is always
`false`, so `parseAllowedActions()` always returned `[]`, meaning **every** call to
`maximo_change_status` and `maximo_send_workflow_response` rejected its action as "not allowed" --
regardless of whether Maximo actually permitted it. This was a pre-existing bug, not introduced by
recent work; it had gone undetected because neither tool had been exercised against a live instance
before now.

Also confirmed live: the status-change action name is **not** `changeStatus` uniformly across
object structures -- MXAPIWO exposes `wsmethod:changeWOStatus` (impl `changeWOStatus`), which
`maximo_change_status` had hardcoded as `"changeStatus"` (a second, independent bug: even with the
parser fixed, the hardcoded name would never have matched).

Fixed by adding one shared, correct parser (`src/maximo/utils/allowedActions.ts`,
`parseAllowedActions`) that every caller now uses, replacing two independent (and both broken)
copies. Maximo's own descriptor per action -- `impl`, `httpmethod` (GET vs POST), `type`
(`wsmethod` vs `system`), `description`, and (when documented) `requestschema` for POST bodies or
`requestqueryparams` for GET query parameters -- is preserved rather than reduced to a bare action
name, since a caller needs to know what to pass, not just what to call.
`statusTools.ts` now auto-detects the status-change action via `findStatusChangeAction()` (matches
the wsmethod whose description is "Change Status", falling back to a `change...Status` name
pattern) instead of hardcoding one, with an `actionName` override field on both
`maximo_plan_status_change` and `maximo_change_status` for object structures the heuristic
doesn't fit. `OSClient.invokeAllowedAction()` replaces the old `invokeAction()` (now unused,
removed): it invokes an action using its own descriptor -- `wsmethod:<impl>` for wsmethod actions,
the bare key for system actions, POST body vs. GET query string per the action's own `httpmethod`
-- instead of assuming every action is a POST + `wsmethod:` prefix.

Live-verified with a real MCP client against a real Maximo instance (all read-only or
non-mutating): `maximo_get_allowed_actions` returned 74 correctly-parsed actions on a work order
(previously 0), including `changeWOStatus`'s real request schema (`date`/`memo`/`status`);
`maximo_invoke_action` successfully invoked a safe GET action (`islocked`); `maximo_plan_status_change`
now correctly reports the transition as `ALLOWED` (previously always `BLOCKED`).

### Added -- `maximo_get_allowed_actions`, `maximo_invoke_action`, `ws_get_allowed_actions`

`maximo_change_status` and `maximo_send_workflow_response` are themselves narrow wrappers over
"check allowedactions, then invoke" -- one for status transitions, one for workflow responses.
Three new tools expose that same mechanism generically, for every other action Maximo allows on a
record that isn't a status change or a workflow response:

- **`maximo_get_allowed_actions`** (read-only, included in `--readonly`): lists every action
  currently allowed on one record, with each action's `httpmethod`, `description`, and (when
  Maximo documents one) `requestSchema`/`requestQueryParams` -- so a caller knows what to pass
  before invoking, rather than guessing.
- **`maximo_invoke_action`** (write): invokes any allowed action by name on one record, re-checking
  it is still allowed immediately before invoking (the same race-condition guard `maximo_change_status`
  already used), then dispatches with the correct HTTP method and action-key prefix per Maximo's
  own descriptor.
- **`ws_get_allowed_actions`** (read-only, included in `--readonly`): returns allowed actions for
  *every* record a working set's query currently matches in one call, by re-running that exact
  query (same `oslc.where`/`pageSize`/`pageno`) with `oslc.select` overridden to `allowedactions`
  -- one call instead of one `maximo_get_allowed_actions` per record. New `OSWorkingSet.getAllowedActionsForAll()`;
  does not touch the working set's loaded records.

Readonly Maximo surface is now 10 tools (was 8): `maximo_get_allowed_actions` and
`ws_get_allowed_actions` join it, `maximo_invoke_action` does not (it can mutate).
Verified with the repository's own `tool_reg_test` registration self-test (88/88 checks,
including the readonly-surface exact-match).

## 1.7.7 -- 2026-09-09

### Fixed -- `ws_next_page` / `ws_previous_page` 404'd against a real Maximo instance

1.7.6's mock test used a bare relative href (`api/os/MXAPIWO?pageno=2&...`), matching the
example doc text that feature was built from. A live end-to-end test against a real Maximo
instance (custom MCP client, `delivery/release/cli.js`, real credentials) -- prompted by a user
report that `ws_next_page` was 404ing in real use -- found Maximo actually returns
`nextPage`/`previousPage.href` FULLY QUALIFIED -- `http://host:port/maximo/api/os/MXAPIWO?
pageno=2&...` -- the same convention it already uses for ordinary record `href`s.
`OSWorkingSet.normalizePageHref()` treated anything not starting with `/` as a bare relative
path and prepended one, turning the absolute href into garbage
(`/http://host:port/maximo/api/os/MXAPIWO?...`); `MaximoClient`'s URL builder then joined that
onto `baseUrl` regardless, producing a nonexistent path and a 404 HTML page from Maximo's web
server (not an OSLC JSON error -- a good sign it never reached the OSLC servlet at all).

Fixed at both points: `MaximoClient` gained a shared `resolveUrl()` used by every request path
(`rawFetch`/`getRaw`/`postBinary`) that uses an absolute `http(s)://` target as-is instead of
prefixing it with `baseUrl` -- correct not just for page navigation but for any future caller
that re-fetches a Maximo-returned href directly. `normalizePageHref()` no longer touches an
already-absolute href. Re-verified against the same live instance: full page1 -> `ws_next_page`
-> page2 -> `ws_previous_page` -> page1 round trip, landing back on the exact same first record.
Added a fully-qualified-href case to the mock test suite (now 27 assertions) so this exact
regression can't silently return, and re-ran `tool_reg_test` (80/80).

**Upgrade note:** if you took 1.7.6 (or public 1.4.8), `ws_next_page`/`ws_previous_page` do not
work against a real Maximo instance until this release.

## 1.7.6 -- 2026-09-08

### Added -- `pageno` on `os_query_builder`, and `ws_next_page` / `ws_previous_page` to actually page

Direct page-number paging, confirmed against a live Maximo instance: Maximo's own
`responseInfo.nextPage.href` (returned when `collectioncount:true` and/or `paging:true` produce
a multi-page result) is literally the same query with `pageno=<n>` appended -- e.g.
`...&oslc.pageSize=100&...&pageno=2` -- so `pageno` is a safe, real input, not an internal-only
cursor value. Added as a 1-based field on `OSLCRequestSchema` / `OSLCRequestSchemaStrict`.

That alone would only get you a specific page manually; the working set layer now actually
tracks and follows Maximo's own paging links, closing the gap identified in 1.7.5 (paging info
was being computed but never surfaced except when `addschema=1` happened to also be set):

- `OSWorkingSet.load()` now unconditionally stashes `responseInfo.nextPage`/`previousPage`/
  `pagenum`/`totalPages` (whenever Maximo returns them) on the instance, independent of
  `addschema`, and still surfaces them in `meta.paging` on every load.
- Two new tools, **`ws_next_page`** and **`ws_previous_page`**, follow those stashed hrefs and
  replace the working set's loaded records with that page's -- the same records area `ws_load`
  populates, so existing `ws_get_records` / `ws_set_active` / etc. keep working unchanged on
  whichever page is current. Both refuse to move (`no_next_page` / `no_previous_page`) when
  Maximo didn't return that link, and refuse (`unstaged_changes_block_paging`) when the working
  set has staged edits on the current page, since replacing the records would silently orphan
  them -- `ws_commit` or `ws_discard` first, then page again.
- Both tools are read-only and registered in `--readonly` mode alongside `ws_load` /
  `ws_get_records` (readonly Maximo surface is now 8 tools, was 6).
- Verified with a 23-assertion mock-backed test exercising forward/backward navigation across
  three pages, both page-boundary errors, the staged-changes guard (confirmed it short-circuits
  before making an HTTP call), and the single-page/no-paging-info case -- plus the repository's
  own `tool_reg_test` registration self-test (80/80 checks, including the readonly-surface
  exact-match).

## 1.7.5 -- 2026-09-03

### Added -- `addschema` on `os_query_builder`, with the response chain actually wired to carry it

Maximo's `addschema=1` (REST/OSLC, 7.6.0.9+) is now exposed as `addschema` on `OSLCRequestSchema` /
`OSLCRequestSchemaStrict`. Adding the flag alone would not have been enough -- two layers in the
response pipeline discarded everything except item data and a row count before this change, so the
schema addschema=1 asks Maximo to inline would have been silently dropped even with the query
param wired up:

1. `MaximoClient.parseResponse()` normalized every response down to `{items, count}`, discarding
   the raw `responseInfo` object entirely (only `oslc:totalCount` was ever read out of it).
2. `OSWorkingSet.load()` then rebuilt its own `meta` from scratch (`count`/`totalCount`/`hasMore`),
   never touching anything else `MaximoClient` returned.

Both fixed: `parseResponse()` now passes `responseInfo` through under `meta.responseInfo` --
verbatim, not reshaped, since the inlined schema's structure mirrors however deep the request's
`oslc.select` went (plain attrs vs. child blocks vs. `rel.<name>{...}` nesting) and there is no
single fixed shape to parse into. `OSWorkingSet.load()` surfaces that as `meta.schema` on `ws_load`'s
response, gated on `addschema=1` actually being present on the URL (checked via a literal substring
match on the built OSLC URL) so an ordinary load doesn't grow a misleading `schema` key that is
really just total-count bookkeeping. `wsTools.ts`'s `ws_load` handler already spread `res.meta`
straight through, so no change was needed there -- it started carrying `schema` for free.

Documented IBM caveat carried into the tool description: Maximo does not carry `addschema=1`
forward onto its own next-page `href`, so paging past the first page needs the flag re-applied on
that page's own `os_query_builder` call.

## 1.7.4 -- 2026-08-30

### Docs -- rewrote the public npm README

`README.npm.md` (the README shipped inside the published npm tarball) was rewritten for a
public audience: internal build-tooling detail (`build.js` / `build-public.js` names, the
public/premium versioning-and-build mechanics section), in-README bug-fix root-cause narrative
that duplicated `CHANGELOG.md`, and an in-README release-history table were removed. Content is
reorganized (installation, configuration, tool reference, orchestration patterns unchanged in
substance) and the file is now pure ASCII -- no em dashes, en dashes, arrows, or curly quotes.
No functional or tool-schema change; `osQueryBuilder.ts` is unchanged in this release.

## 1.7.3 -- 2026-08-30

### Added -- `domaininternalwhere` on `os_query_builder`

Parent-level Maximo OSLC "SynonymDomain Internal Filters" are now exposed directly on
`OSLCRequestSchema` / `OSLCRequestSchemaStrict`, rendering `domaininternalwhere` on the
built URL alongside `oslc.where` (`GET <collection uri>?oslc.where=...&domaininternalwhere=status!=APPR,INPRG`).
Filters on the INTERNAL value(s) of an attribute bound to a synonym domain (e.g. WOSTATUS)
rather than the external display value `where`/`rawWhere` compare against. Grammar:
`<attrName>[=|!=]internalVal1,internalVal2,...` -- `=` generates SQL IN, `!=` generates SQL
NOT IN, values are a comma-delimited non-empty list with no null entries -- validated against
that exact grammar at build time (`normalizeDomainInternalWhere`) so a malformed value fails
fast instead of Maximo silently discarding the filter. It is independent of `oslc.where`:
Maximo ANDs it server-side, it is never merged into the `where` clause itself. The existing
per-relationship `domaininternalwhere` on `childOptions` entries (already present, scoped to
one child collection) now shares the same description text for consistency but is unchanged
in behavior/validation -- still rendered raw, no grammar check.

## 1.7.2 -- 2026-08-30

### Added -- `tlrange` / `tlattribute` timeline filters on `os_query_builder`

Parent-level Maximo OSLC "Timeline Filters" are now exposed directly on
`OSLCRequestSchema` / `OSLCRequestSchemaStrict`, rendering `tlrange` and
`tlattribute` on the built URL (`GET /oslc/os/mxapiwodetail?tlrange=-3M&tlattribute=reportdate`).
`tlrange` follows Maximo's own `TimelineFilterHelper.getDate` grammar --
`<sign><n><unit>` where sign is `+`/`-`/`+-` and unit is one of `D`/`W`/`M`/`Y`/`h`/`m`/`s`
(case-sensitive -- `M` is months, `m` is minutes) -- and is validated against that
exact grammar at build time (`normalizeTlRange`) so a malformed value fails fast
instead of Maximo silently discarding the filter. `tlattribute` names the date
attribute to index on and may append `=<ISO date>` to pin the index date instead
of defaulting to now; it is passed through raw, unvalidated. The two are required
together. The existing per-relationship `tlrange`/`tlattribute` on `childOptions`
entries (already present, scoped to one child collection) now share the same
description text for consistency but are unchanged in behavior/validation --
still rendered raw, no grammar check.

## 1.7.1 -- 2026-08-26

### Added -- `extendsObject` on MBO metadata

`MAXOBJECTCFG.EXTENDSOBJECT` is now selected by `MAXMCPMETADATA` and stored on
each object's meta blob. `maximo://object/{objectName}` returns `extendsObject`
(SR -> TICKET, WOACTIVITY -> WORKORDER, empty for a root MBO). Clients can walk
that chain and merge `relationships/compact` so inherited names such as ASSET
are visible on an SR query. Redeploy the automation script and re-sync metadata;
existing local DBs do not gain the field until then.

## 1.4.10 -- 2026-09-11 (public npm release)

Public cut of the `allowedactions` parser fix and the three new generic action tools (see 1.7.8
above). `maximo_change_status` and `maximo_send_workflow_response` were broken in every prior
public release back to their introduction -- they rejected every action as "not allowed"
regardless of whether Maximo actually permitted it. **38-tool** surface, up from 35.

## 1.4.9 -- 2026-09-09 (public npm release)

Public cut of the `ws_next_page`/`ws_previous_page` 404 fix (see 1.7.7 above). If you took
1.4.8, page navigation does not work against a real Maximo instance until this release.

## 1.4.8 -- 2026-09-08 (public npm release)

Public cut of `pageno` plus the new `ws_next_page` / `ws_previous_page` tools (see 1.7.6
above). **35-tool** surface, up from 33 -- the two page-navigation tools are additive, nothing
existing changed shape.

## 1.4.7 -- 2026-09-03 (public npm release)

Public cut of the `addschema` support and its response-chain fix (see 1.7.5 above). Same
**33-tool** surface as 1.4.6; nothing else changed shape.

## 1.4.6 -- 2026-08-30 (public npm release)

Public cut carrying the README rewrite (see 1.7.4 above). No tool or schema change from 1.4.5.

## 1.4.5 -- 2026-08-30 (public npm release)

Public cut of the `domaininternalwhere` synonym-domain internal-value filter (see 1.7.3
above). Same **33-tool** surface as 1.4.4; nothing else changed shape. An agent written
against 1.3.7 or later runs unchanged.

## 1.4.4 -- 2026-08-30 (public npm release)

Public cut of the `tlrange`/`tlattribute` timeline filters (see 1.7.2 above). Same
**33-tool** surface as 1.4.3; nothing else changed shape. An agent written against
1.3.7 or later runs unchanged.

## 1.4.3 -- 2026-08-26 (public npm release)

Public cut of the `extendsObject` field. Same **33-tool** surface as 1.4.2.
Redeploy `MAXMCPMETADATA` and re-sync. Same change as 1.7.1.

## 1.4.2 -- 2026-08-24 (public npm release)

Public cut carrying the 1.7.0 `childOptions` fix (see below) onto the 1.4.1 base layer.
Same **33-tool** 1.3.8 surface, `--copilot-mode` and `--readonly` included. `childOptions`
`where` / `orderBy` / `limit` now filter and sort child rows -- see the 1.7.0 entry below
for the full root cause and a live-verified example; nothing else changed shape. An agent
written against 1.3.7 or 1.3.8 runs unchanged.

## 1.4.1 -- 2026-08-22 (public npm release)

Public cut of the current base layer. Same **33-tool** 1.3.8 surface, `--copilot-mode`
included, plus `--readonly` / `MCP_READONLY`. The 12 Enterprise configuration tools are not
in this package. An agent written against 1.3.7 or 1.3.8 runs unchanged.

## 1.7.0 -- 2026-08-24

### Fixed -- `childOptions` where/orderBy/limit now actually filter and sort child rows

Two bugs, found live, both corrected the 1.3.8 conclusion that "Maximo accepts these
child params and then ignores them":

1. **Wrong MBO prefix past one hop.** Maximo's engine resolves child filter params as
   `<pmbo>.<relationship>.<property>`, where `pmbo` is the MBO that owns THAT SPECIFIC
   relationship hop -- it changes at every nesting level, it is not always the object
   structure's top-level primary object. `renderChildOptions` always used the single
   top-level primary MBO for every entry, correct only one hop deep.
   `childOptions[]` entries now accept an optional `path: string[]` -- the full
   relationship-name chain from the primary object down to and including the filtered
   relationship (e.g. `['MODIFYWORKLOG','PERSON','SMS']`). Each hop is resolved against
   `getObjectRelationships()` of the MBO that owns it (mirrors the write-path resolution
   `OSWSValidator` already uses for nested child validation). Resolution is best-effort:
   a relationship not found in the locally synced metadata (real for ticket-hierarchy
   objects like SR/INCIDENT that inherit relationships from a base class) degrades to a
   warning and the pre-fix top-level-MBO rendering, never a hard failure -- some real,
   Maximo-accepted relationships simply aren't enumerated by the per-object metadata sync.
2. **The param KEY itself must be lowercase.** `OslcUtils.handleSubQbeAndSort` only
   lowercases the MBO/relation names it resolves internally -- the HTTP query-string
   parameter name lookup that finds the param in the first place is a case-sensitive
   string match, done before any of that. Every version of this code (including the
   fix for bug 1, initially) rendered the key using whatever case the metadata store
   returns (uppercase), so the param was silently never found -- indistinguishable from
   "Maximo ignores it." The `<pmbo>.<relationship>` prefix is now rendered lowercase;
   the `.property` suffix (`.where`, `.orderBy`, ...) already matched the engine's
   literal casing and is unchanged.

Live-verified end to end: `MXOBJECTCFG` (`objectname="ASSET"`) with
`rel.MAXATTRIBUTECFG{attributename,maxtype}` selected and a `childOptions` filter to
`ATTRIBUTENAME="ASSETNUM"` now returns exactly 1 attribute row, down from 205
unfiltered.

Also added: `noLimit`, `searchTerms`, `searchAttributes`, `domaininternalwhere` per-
relationship options (present in Maximo's engine, absent from the schema before). New
safety default: a `childOptions` entry with no explicit `limit` gets one
(`MAXIMO_CHILD_REL_DEFAULT_LIMIT`, default 50) to bound nested fetches; set
`noLimit:true` to opt out -- does not yet cover a bare `rel.` select with no
corresponding `childOptions` entry (deferred; would need a real select-string parser).
A `childOptions` entry filtering a relationship that doesn't appear to be selected now
gets a warning instead of silently doing nothing.

`childCollection` and the `rel.<name>{...}` select syntax are unchanged -- still the
simplest path for a single-parent, single-hop filter, and the only way to page or
`collectioncount` child rows.

## 1.6.2 -- 2026-08-22

### Added -- `--readonly` / `MCP_READONLY`

A process flag that suppresses write tools at registration time. The live surface is
`maximo_get_metadata`, `os_query_builder` (`opAction=query` only; update/patch/delete are
rejected), `ws_load`, `ws_get_records`, `ws_list_attachments`, `ws_get_attachment`, plus
`mcp_server_status` and `mcp_read_logs` (no `--dev-mode` required). Working-set writes, ctx
tools, audit, status, workflow, and premium configuration tools are not registered.
`mcp_server_status` reports `server.readonly`.

## 1.3.8 -- 2026-08-17 (public npm release)

The first npm release since 1.3.7. It is the **1.3.7 tool surface** -- the same 33 tools,
`--copilot-mode` included -- plus the read-path and working-set fixes below. No tool was
removed, renamed or changed shape, and no parameter changed meaning, so an agent written
against 1.3.7 runs unchanged. The 12 Enterprise tools (configuration, diagnostics, App
Designer, automation scripts) are not built into this package.

Every fix below was verified against a live Maximo instance.

### Fixed -- `like` produced a query Maximo refuses to parse

The builder emitted the OSLC `LIKE` keyword, which Maximo's parser rejects outright, so every
wildcard search failed with `BMXAA8744E ... Encountered " <IDENTIFIER> "LIKE ""`. It now emits
wildcard equality (`description="%pump%"`), which Maximo accepts. Only previously failing calls
change behaviour.

### Fixed -- `orMode: true` produced a query Maximo refuses to parse

The builder joined conditions with `or` **and** sent `opmodeor=1`. Maximo accepts only `and`
inside `oslc.where` once `opmodeor=1` is present, so the request failed to parse instead of
returning a union. Conditions are now always joined with `and`, with OR semantics coming from
`opmodeor=1` alone. The same normalisation applies to `rawWhere` containing `or`, and to
`childOptions` for consistency.

### Fixed -- `collectioncount: true` never surfaced a total

Maximo returned the count and the server dropped it in two places: the working set discarded
`res.count`, and the lean encoder omitted `meta` entirely. `ws_load` now returns
`meta.totalCount` (records matching in Maximo), `meta.count` (rows in this page) and
`meta.hasMore`, in both lean and full responses. `MaximoClient` also reads the total from both
the prefixed and unprefixed response shapes.

### Added -- `childCollection` on `os_query_builder`

Queries a single parent's child collection as its own collection
(`/api/os/{os}/{parentRecordId}/{relationship}`), so `select`, `where`, `orderBy`, `pageSize`
and `collectioncount` apply to the **child** rows. This is the only way to filter child rows.

Optional `responseOs` re-renders the far side of the relationship through another object
structure, applying that structure's business rules and exposing its own children; it is
required to reach the far side's children. The value is normalised to upper case, because
Maximo answers a lower-case `responseos` with an HTTP 500.

Purely additive -- existing queries do not go near this path.

### Changed -- `childOptions` now reports that Maximo ignores it

Maximo accepts child `where` / `limit` / `orderBy` and then returns every child row regardless,
so these could never filter anything. The parameters are still sent, so no existing call
changes, but responses now carry a `warnings` array naming the ignored options and pointing at
`childCollection`. `tlrange` / `tlattribute` are unaffected.

### Fixed -- `relatedObjects` always reported `relation: null`

The schema loader read `relation` from `property.items` when Maximo declares it on the property
itself, so the configured relationship name was lost for all 808 child properties across 469
object structures. `relation` and `cardinality` are now populated. Sub-schema keys and
`objectName` now come from Maximo's own `objectName` rather than the sub-schema URI's last
segment; across a full sync the two agree everywhere except `REP_REPDESIGN`, where the object
is genuinely `REPORTDESIGN` and the old URI-derived `REPORT_DESIGN` was wrong for dot-notation
filtering. Values populate on the next metadata sync.

This distinction matters: the relationship name and the object name are usually different, and
each is required in a different place. Supplying the wrong one returns zero rows without an
error.

### Fixed -- `maximo://object/{object}/relationships/compact` was unreachable

A route-ordering bug matched the general `/relationships` branch first, so the compact endpoint
could never be reached and `/relationships/search/{target}` returned the entire relationship
list instead of the requested edge. Routing is now ordered most-specific-first, and the compact
response carries `relationshipName` + `targetObject` + `whereClause` (the join keys) instead of
verbose `remarks`, which is what a query builder actually needs.

## 1.6.1 -- 2026-08-05

### Fixed -- `maximo_appdesigner_edit` commit response overflowed the tool-output budget

Found in live testing on a real 69KB SR presentation: the write committed correctly, but the
`commit` response embedded the Working Set executor result, which echoes the whole staged child
payload back -- i.e. the full ~70KB presentation CLOB. The response itself (~74KB) then blew the
MCP tool-output token limit. The delta tool exists so the CLOB never crosses the tool channel;
this leaked it back on the return path.

- `commit` now passes the executor result through `compactCommitResult()`: it strips the
  `presentation` CLOB and truncates any other long string, keeping the useful signal (child
  `_action` tags, hrefs, status). The `stage_failed` / `commit_failed` error details are
  sanitised the same way, since a failed commit's per-op `results` can echo the CLOB too.
- Regression-guarded in `presentationSession_test.ts` (the fake engine now reproduces the echo;
  the test asserts the commit response stays small and contains no raw presentation CLOB).

## 1.6.0 -- 2026-08-04

### Added -- App Designer presentation delta-edit (`maximo_appdesigner_edit`)

A structured edit lifecycle for a Maximo Application Designer presentation
(`MAXPRESENTATION.presentation` on `DMMAXAPPS`) that never transports the full document
through the tool-call channel.

The problem it fixes: the `app-designer-change` recipe needs a full read-modify-write of the
presentation CLOB, which routinely runs to **70KB+**. An agent cannot reliably ship that whole
document back through `ws_add_child_record` in one tool call -- it truncates and corrupts the
JSON. Every control in a Maximo presentation carries a **unique `id`**, so the change is instead
expressed as a small anchored fragment.

- **New module `src/maximo/presentation/`**:
  - `xmlFragment.ts` -- a pure, dependency-light delta engine. Locates an element by its unique
    `id` (handling nested same-name elements, self-closing controls, comments/CDATA), and
    splices `insert` (before/after an anchor), `replace` or `remove` at the exact character span.
    It does **not** reparse/reserialise the whole CLOB, so the committed document differs from the
    original **only** where the intended change is -- a clean single child diff and a trivial
    rollback. `xml2js` is used only to validate well-formedness of the fragment and merged result.
  - `PresentationEditSession.ts` -- a server-side session that owns the full CLOB.
- **`maximo_appdesigner_edit`** tool, one action per lifecycle step:
  - `init { app }` -> reads the current presentation + `maxpresentationid` into a session; returns
    the session id and the existing control ids to anchor to (never the full CLOB).
  - `modify { sessionId, ops }` -> applies ordered `insert`/`replace`/`remove` ops. Aborts on the
    first failure (unknown/ambiguous/duplicate id, malformed fragment) leaving state unchanged.
  - `preview { sessionId }` -> compact diff (ids added/removed, sizes, well-formedness) only.
  - `commit { sessionId, confirm }` -> stages exactly **one** `MAXPRESENTATION` child `Change`
    (matched on `maxpresentationid`, same shape the recipe prescribes) and commits through the
    existing Working Set gates. Human-gated on `confirm:true`; aborts and sends nothing if the
    merged document is not well-formed.
  - `verify { sessionId }` -> re-reads from Maximo and confirms the persisted document (byte and
    id match).
- The agent's payload stays in the KBs (the changed fragment), not tens of KB of full app. The
  full CLOB only ever moves server<->Maximo over HTTP, which has no such limit.
- Unchanged: a full server restart (or presentation-cache rebuild) is still required before an
  out-of-band `DMMAXAPPS` write surfaces in the UI -- `commit` says so explicitly.

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
