# Versions and access

Single source of truth for what is publicly installable.
If any other page disagrees with this one, this page is correct.

## At a glance

| Product | Published | Current line |
|---------|-----------|--------------|
| **maximo-mcp-server** | **2.1.1** (npm) | **2.1.1** -- current release |
| **maximo-kit** | **0.1.1** (GitHub Releases) | **0.5.0** -- on request |

Contact: **soumyaprasad.rana@gmail.com**

## maximo-mcp-server

| | Version | How to get it |
|---|---|---|
| **Published (npm)** | **2.1.1** | `npm install -g @soumyaprasadrana/maximo-mcp-server` |

**One package, every tool.** Everything the server can do ships in the npm package -- reads,
working-set writes, status changes, workflow, reports, async commits and the configuration
tools (Configure Database, Admin Mode, system properties, read-only SQL, live cache reload, App
Designer editing). There are no paid tiers and no separate builds. What you enable is your
choice: `--readonly` keeps the read path only, the ten configuration tools register only with
`--copilot-mode`, and `--disabled-tools` hides any tool.

**License.** The software is free to use, but it is not open source. It is proprietary and free
for non-commercial use (personal, educational, research) under the terms in [LICENSE](https://github.com/soumyaprasadrana/maximo-mcp-server/blob/main/LICENSE).
For commercial use or redistribution, contact the author.

**2.1.1 is the current npm release** (2026-11-09).

### What 2.1.1 fixes

- **Object structure search** (`maximo://os/search/...`) now finds the expected object structure:
  relevance-ranked keyword hits, scoring on the apimeta title and the object structure name, and
  reporting structures ranked lower. Works in on-demand mode and on existing databases without a
  resync; no MAXMCPMETADATA change.

### What 2.1.0 adds over 2.0.0

- **Security:** every request is pinned to the configured Maximo (the API key can no longer be
  sent to another host through `basePath` or a foreign URL); credentials never follow redirects.
- **Workflow:** open assignments with their routes, `maximo_complete_workflow_assignment` and
  `maximo_start_workflow`.
- **Status changes** are checked against Maximo's next-status list.
- **New read-only tools:** `maximo_lookup_values` (incl. table domains), `maximo_aggregate`
  (group by), `maximo_list_reports` / `maximo_run_report` (BIRT), `maximo_integration_errors`,
  and opt-in `maximo_read_server_log`.
- **`ws_add_attachment`**, response and concurrency limits, truthful auth errors (MAS login
  redirects, BMXAA reasons), `mcp_server_status` on every server.

### What 2.0.0 added over 1.4.16

- **One edition:** the configuration tools and `ws_commit_status` joined the npm package.
  Breaking: the ten configuration tools need `--copilot-mode`.
- **Tool exposure control:** `MCP_DISABLED_TOOLS` / `--disabled-tools` hides any tool.
- **Per-caller identity over HTTP:** `--caller-apikey` runs each request as the Maximo user
  whose API key it carries; working sets become private to their creator.
- **On-demand metadata:** `--reconcile-lazy` -- no startup sync; each object structure is
  fetched the first time a tool needs it.
- **Working sets that survive a restart:** `--ws-persist`, with crash-safe commits.
- **No native embedding dependencies:** `@xenova/transformers` and `onnxruntime-node` are no
  longer installed; `MCP_EMBEDDINGS_MODE=local` needs a manual install (breaking for `local` users).
- **Read-only mode** also registers `ws_remove`.
- **Security:** `maximo_get_url` checks the decoded servlet path, so an encoded or
  `;`-suffixed script path cannot pass as a read.

### Read-only mode

`--readonly` registers: `maximo_get_metadata`, `os_query_builder` (query only), `ws_load`,
`ws_next_page`, `ws_previous_page`, `ws_get_records`, `ws_remove`, `ws_get_allowed_actions`,
`ws_list_attachments`, `ws_get_attachment`, `maximo_get_allowed_actions`, `maximo_get_url`,
`maximo_get_workflow_assignments`, `maximo_lookup_values`, `maximo_aggregate`,
`maximo_list_reports`, `maximo_run_report`, `maximo_integration_errors`, plus the MCP
diagnostics. `MCP_ENABLE_SCRIPT_GET` optionally adds a GET-only
`maximo_invoke_automation_script`; `MCP_ENABLE_SERVER_LOGS` adds `maximo_read_server_log`.

### Earlier releases

Everything before 2.0.0 -- the query builder, paging, generic actions, status changes
with electronic signatures, file import, the App Designer delta-edit, the configuration safety
guards and async commits -- is recorded in [CHANGELOG.md](https://github.com/soumyaprasadrana/maximo-mcp-server/blob/main/CHANGELOG.md).

## maximo-kit

| | Version | How to get it |
|---|---|---|
| **Published (GitHub Releases)** | **0.1.1** | Release asset URLs on the [Releases page](https://github.com/soumyaprasadrana/maximo-kit/releases) |
| **Current line** | **0.5.0** | On request -- see [Contact](#contact) |

**0.1.1 is the last public release** of the kit, and no further public releases are planned for
now. The kit has continued to develop -- **0.5.0** is the current line and it moves forward --
but that work is not distributed publicly.

The 0.1.1 install instructions remain valid. That release was the on-ramp: it shows the shape
of the workflow (design -> plan -> stage -> preview -> validate -> approve -> commit -> verify)
and enough recipes to be useful on its own.

### What 0.5.0 holds (not public)

24 change/analyze recipes, 5 playbooks, 15 commands and 70 knowledge files, plus the
evidence-backed rules earned from live runs -- Same As parity, domain/attribute parity,
the Configure Database lifecycle, presentation and lookup anatomy, and the delete-capability
matrix. 0.5.0 adds per-phase evidence artifacts for multi-commit changes and adopts the
maximo-mcp-server App Designer delta-edit lifecycle for presentation edits.

## Contact

**soumyaprasad.rana@gmail.com**

Get in touch for:

- a **commercial licence** for maximo-mcp-server
- **maximo-kit 0.5.0** and onward
- evaluation or partnership

Public repositories:

- [maximo-mcp-server](https://github.com/soumyaprasadrana/maximo-mcp-server)
- [maximo-kit](https://github.com/soumyaprasadrana/maximo-kit)
