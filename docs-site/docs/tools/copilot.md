# Copilot Tools

::: warning v1.5.0 -- NOT AVAILABLE ON npm
Everything on this page is part of the **1.5.0** line. The last version published to the npm
registry is **1.3.7**, so `npm install` will **not** give you these tools.

They are documented here so the capability is public even where the build is on request.
For access: **soumyaprasad.rana@gmail.com**. See [Versions and access](/versions).
:::

Copilot tools take the server past reading and writing business data into **governed platform
configuration** -- Configure Database, Admin Mode, system properties, and diagnostics that the
Object Structures cannot reach.

They exist because a handful of Maximo configuration operations are either impossible over
OSLC, or possible but quietly dangerous. Each one below closes a specific, measured gap.

## Why this matters

Before 1.5.0, a configuration workflow driven by an agent hit a wall: it could stage a change
but not apply it, could not tell whether a change needed a maintenance window, could not read a
system property, and had no protection against Maximo's own configuration pitfalls -- the ones
the platform accepts silently and only surfaces later.

1.5.0 closes all four: it drives Configure Database end to end, reads and sets properties, and
adds guards that catch a dangerous change at preview instead of at the database.

## Configuration safety guards

Not a tool, but the reason the rest are safe to expose. Guards run between staging and sending
and either repair a payload or refuse to send it -- so a whole class of Maximo configuration
pitfalls is caught at preview and never reaches your instance.

**The pitfall they close.** Maximo's Same As inheritance is powerful but unforgiving over the
REST API. An attribute whose type or length does not match its master is accepted without
complaint and then propagated across the entire inheritance family. On a common shared key such
as `ASSET.ASSETNUM`, that single mismatch can fan out to **hundreds of attributes across dozens
of objects** -- with no error raised, so it is invisible until a later Configure Database. This
is platform behavior: it is present whether you edit Same As over REST or in the UI.

The `sameas-parity` guard removes that risk. It repairs an inherited definition that was omitted
and **blocks** one that contradicts its master, naming the exact values required -- at preview,
before anything is sent to Maximo.

- Guards run in **both** `ws_preview_changes` (as blocking `guard_violations`, distinct from the
  advisory `validation_warnings`) and `ws_commit`, where nothing is sent.
- A guard that cannot evaluate **blocks** rather than letting the change through.
- Adding a guard is one file plus one registry line, so new hazards are cheap to encode.

## Configure Database

The lifecycle no longer dead-ends at a manual UI click.

| Tool | Purpose | Gate |
|------|---------|------|
| `maximo_dbconfig_status` | Config level (`NONE` / `NONSTRUCT` / `STRUCT`), Admin Mode state, and which IBM permissions the API user holds | read-only |
| `maximo_dbconfig_apply_status` | Poll a run -- one `phase`: `CLEAN` / `PENDING` / `RUNNING`, plus Maximo's own messages | read-only |
| `maximo_dbconfig_discard` | Discard **pending** configuration; nothing already applied is touched | `confirm` + IBM `CONFIGUR.REMOVE` |
| `maximo_dbconfig_apply` | Apply Configuration Changes -- **alters physical schema** | `confirm` + `confirmToken` + IBM `CONFIGUR.CONFIGURE` |
| `maximo_admin_mode` | Start / end / cancel an Admin Mode transition | `confirm` + IBM `CONFIGUR.ADMINMODE` |

Three things worth knowing:

- **Only `STRUCT` needs Admin Mode.** A non-structural change no longer costs a maintenance
  window it never required -- the agent can now check instead of assuming.
- **`apply` refuses** to start a structural apply while Admin Mode is off, refuses while a run
  is already in progress, and reports `nothing_to_apply` when nothing is pending.
- **Apply is asynchronous.** Success means *started*. Poll `maximo_dbconfig_apply_status` until
  `phase` is `CLEAN`.

**Check the blast radius before applying.** If far more is pending than the change you made,
discard and re-stage rather than applying -- discarding is fast and reversible; applying a
cascade is neither.

## Diagnostics and configuration access

| Tool | Purpose | Gate |
|------|---------|------|
| `maximo_sql_query` | Read-only SQL for questions the Object Structures cannot answer -- above all "what did that configuration change actually alter?" | human approval on **every** call |
| `maximo_system_property` | Get / list / set system properties, with live-refresh and an explicit `restartRequired` flag | `confirm` on `set` |
| `maximo_copilot_setup` | Install / inspect / remove the utility scripts and their signature options | dry-run by default; never writes grants |

`maximo_sql_query` is deliberately narrow: a single statement, `SELECT` or `WITH ... SELECT`
only, every DML and DDL keyword refused before the database is touched, results capped, and the
connection always released. It can read any table, so results are treated as sensitive and
approval is per query -- a previous yes does not cover the next one.

## Permission model

Access is enforced by **Maximo**, not by this server.

Each utility is a Jython automation script carrying a signature option on an **existing IBM
application** -- `CONFIGUR` (Database Configuration) and `PROPMAINT` (System Properties). No new
application is created, and no navigation or presentation is touched.

- Maximo's REST script handler enforces the option and rejects an ungranted caller with
  `BMXAA0028E` **before the script runs**.
- **An administrator must grant the options.** The server never writes `APPLICATIONAUTH` in
  either direction; `maximo_copilot_setup` prints exactly what to grant and where.
- Privileged actions additionally require the **genuine IBM permission** (`CONFIGUR.CONFIGURE`
  for apply, `CONFIGUR.REMOVE` for discard, `CONFIGUR.ADMINMODE` for Admin Mode), so a
  server-side grant can never substitute for Maximo's own security.
- Installation is reversible: `maximo_copilot_setup mode='uninstall'` removes the scripts and
  the options, returning the IBM applications to their original state.

## Setup

```bash
# 1. install (writes to Maximo, so it is an explicit step)
maximo-mcp-server --setup-copilot --copilot-mode \
  --maximo-url https://your-maximo/maximo --maximo-api-key YOUR_KEY

# 2. an administrator grants the printed options in Security Groups

# 3. verify
maximo-mcp-server --copilot-status --maximo-url ... --maximo-api-key ...
```

Add `--copilot-dry-run` to preview without writing. Use `--uninstall-copilot` to remove
everything. On normal startup the server only **verifies and reports** -- it never provisions
on its own.
