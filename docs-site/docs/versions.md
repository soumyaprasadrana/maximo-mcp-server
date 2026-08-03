# Versions and access

Single source of truth for what is publicly installable and what is available on request.
If any other page disagrees with this one, this page is correct.

## At a glance

| Product | Published | Current line |
|---------|-----------|--------------|
| **maximo-mcp-server** | **1.3.7** (npm) | **1.5.0** -- on request |
| **maximo-kit** | **0.1.1** (GitHub Releases) | **0.4.0** -- on request |

Contact: **soumyaprasad.rana@gmail.com**

## maximo-mcp-server

| | Version | How to get it |
|---|---|---|
| **Published (npm)** | **1.3.7** | `npm install -g @soumyaprasadrana/maximo-mcp-server` |
| **Current line** | **1.5.0** | On request -- see [Contact](#contact) |

**1.3.7 is the last version published to the npm registry.** Development continued through
1.4.1, 1.4.2, 1.4.5 and 1.5.0, but those builds are not on the public registry. There is no
later public tag to install: `npm install` gives you 1.3.7, and that is expected.

The install instructions throughout this site remain valid and supported. They describe the
last public registry version, not an abandoned one.

### What 1.4.x - 1.5.0 added (not on npm)

**Configuration safety guards.** Some Maximo configuration writes are accepted without error
while altering far more than the record you edited -- a class of platform pitfall the guards
catch at preview so it never reaches your instance. The clearest example is Same As: over the
REST API, an attribute whose type or length does not match its master is propagated across the
whole inheritance family, and on a common shared key that can be hundreds of attributes across
dozens of objects, with no error raised. The `sameas-parity` guard enforces the match before
anything is sent.

**Configure Database, end to end.**

| Tool | What it does | Gate |
|------|--------------|------|
| `maximo_dbconfig_status` | Read-only config level (`NONE` / `NONSTRUCT` / `STRUCT`), Admin Mode state, permissions held | read-only |
| `maximo_dbconfig_apply_status` | Read-only poll -- one phase: `CLEAN` / `PENDING` / `RUNNING` | read-only |
| `maximo_dbconfig_discard` | Discard **pending** configuration; nothing applied is touched | confirm + IBM `CONFIGUR.REMOVE` |
| `maximo_dbconfig_apply` | Apply Configuration Changes -- alters physical schema | confirm + token + IBM `CONFIGUR.CONFIGURE` |
| `maximo_admin_mode` | Start / end / cancel an Admin Mode transition | confirm + IBM `CONFIGUR.ADMINMODE` |

Only `STRUCT` changes need Admin Mode, so a non-structural change no longer costs a
maintenance window it never required.

**Diagnostics and configuration access.** `maximo_sql_query` (read-only SQL, single `SELECT`,
DML/DDL refused server-side, human approval on every call), `maximo_system_property`
(get / list / set), and `maximo_copilot_setup` (install / inspect / remove the utility scripts,
dry-run by default). Full reference: [Copilot Tools](/tools/copilot).

Access is enforced by Maximo itself: each utility carries a signature option on an existing
IBM application, and an administrator must grant it. The server never writes
`APPLICATIONAUTH`, and privileged actions additionally require the genuine IBM permission.

**Reliability.** Asynchronous commit with polling for configuration commits that outlive an
MCP client timeout; a dedicated long-operation connection pool so slow commits are not severed
mid-flight; and failures that stop reporting themselves as successes, with Maximo's `BMXAA*`
codes surfaced verbatim.

Full history: [CHANGELOG](https://github.com/soumyaprasadrana/maximo-mcp-server/blob/main/CHANGELOG.md).

## maximo-kit

The Spec Kit extension that drives this server through a design-first, recipe-driven
configuration workflow.

| | Version | How to get it |
|---|---|---|
| **Published (GitHub Releases)** | **0.1.1** | [Releases page](https://github.com/soumyaprasadrana/maximo-kit/releases) |
| **Current line** | **0.4.0** | On request -- see [Contact](#contact) |

**0.1.1 is the last public release**, and no further public releases are planned for now.
0.4.0 is the current line and it moves forward, but that work is not distributed publicly.

Repository: [maximo-kit](https://github.com/soumyaprasadrana/maximo-kit) --
documentation: <https://soumyaprasadrana.github.io/maximo-kit/>

## Why it is arranged this way

The documentation stays public deliberately. Anyone can read how the tools work, what the
Object Structures are, which gates exist and why, and follow what the product can do as it
develops. What is gated is the current distribution, not the knowledge.

## Contact

**soumyaprasad.rana@gmail.com**

Get in touch for:

- **maximo-mcp-server 1.5.0** (anything newer than the public 1.3.7)
- **maximo-kit 0.4.0** and onward
- evaluation, partnership, or private / tailored builds
