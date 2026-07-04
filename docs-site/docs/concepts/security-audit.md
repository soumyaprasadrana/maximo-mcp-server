# Security & Audit

The server is built for governed, enterprise use. Three mechanisms keep writes controlled and traceable.

## App-level permission gates

Before staging any write (`INSERT` / `UPDATE` / `DELETE`), the server resolves the **authorizing application** for the target Object Structure and checks its Maximo permissions via the allowed-app service.

- Reads are permitted by default.
- Writes are denied with `no_authapp_for_os` when no authorizing app can be resolved and the operation isn't otherwise allowed.
- On permission-check failure the server is conservative: reads allowed, writes denied.

This means an agent cannot stage a change to an object the connected credentials aren't allowed to modify.

::: tip Copilot mode
When `MCP_COPILOT_MODE=true`, Migration Manager (`DM`-prefixed) Object Structures are writable through the `MIGRATIONMGR` `useWith` gate, enabling the experimental Developer Copilot workflow. See [Configuration → Copilot mode](/guide/configuration#maximo-developer-copilot-mode).
:::

## OAuth 2.0 (HTTP transport)

Running with `MCP_TRANSPORT=http` turns on a built-in OAuth 2.0 authorization server:

- **Grant:** `client_credentials`
- **Token:** signed JWT (HS256); the signing secret is auto-generated and persisted
- **Client registry:** stored in the metadata SQLite DB; secrets are **hashed** and unrecoverable after creation

Every MCP connection must present a valid `Authorization: Bearer <token>`. See [Connecting Clients → HTTP + OAuth](/guide/clients#http-transport-with-oauth-2-0).

## Audit logging

Set `AUDIT_ENABLED=true` to record every staged Working Set operation to an append-only, monthly-rotated SQLite store.

- Each entry captures the operation (create/update/delete/commit), the target, before/after values or diff, source tool, and success flag.
- Query it from within an agent with **`maximo_get_audit_logs`** (filter by time range, working set, OS, or operation).
- Retention is controlled by `AUDIT_RETENTION_MONTHS` (default 12).

| Setting | Default | Purpose |
| --- | --- | --- |
| `AUDIT_ENABLED` | `false` | Turn audit logging on |
| `AUDIT_DB_DIR` | `./audit` | Where monthly audit DBs are written |
| `AUDIT_RETENTION_MONTHS` | `12` | How long to keep audit data |

## Defense in depth

- **Nothing writes without a preview.** The staged model guarantees a human-readable diff before any commit.
- **Validation is advisory, Maximo is authoritative.** The server surfaces warnings but lets Maximo enforce the real rules.
- **Least surprise on children.** Natural-key diffing means untouched child rows are never disturbed — see [Child Records](/concepts/child-records).
