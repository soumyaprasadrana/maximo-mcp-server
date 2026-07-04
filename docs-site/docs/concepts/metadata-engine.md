# Metadata Engine

The Metadata Engine is the server's local knowledge of your Maximo instance. It is what lets an agent **discover before it acts** — finding the right Object Structure, fields, and relationships instead of guessing.

## What it stores

Synced from Maximo into a local SQLite database (`<data-dir>/data/meta.db`):

- **Object Structures** — every OS exposed by your instance, with its primary object and description
- **Schemas** — the API-scoped JSON schema for each OS (queryable parent fields)
- **Sub-schemas** — the schema of each child object in a relationship, including its natural-key (`pk`) fields
- **Objects, attributes, relationships** — MBO-level metadata (types, domains, lengths, required flags) via the `MAXMCPMETADATA` script

## How agents use it — `maximo_get_metadata`

Discovery happens through `maximo://` URIs:

| URI pattern | Returns |
| --- | --- |
| `maximo://os/search/{query}` | Object Structures matching a keyword — **start here** |
| `maximo://os/{osName}/schema` | Parent-object field names for `select` / `where` |
| `maximo://os/{osName}/relatedObjects` | Child relationships (relationship name + object name) |
| `maximo://os/{osName}/subschemas/{childObject}` | Child object field names (comma-separate for several) |

Typical flow: **search** → **schema** → **relatedObjects** → **subschemas** → `os_query_builder`.

## Search

Object Structure search combines keyword matching with optional semantic (vector) search. Set `MCP_EMBEDDINGS_MODE=local` (or `openai`) to enable embeddings; the default `none` uses keyword + hybrid ranking and is recommended for production. `MAXIMO_OS_SEARCH_LIMIT` caps how many candidates are returned.

## Sync lifecycle

Metadata is downloaded on first startup in three resumable stages (API metadata → schemas → MBO metadata). Progress is checkpointed, so an interrupted sync resumes rather than restarting. While a sync is in progress, normal tools return `metadata_sync_in_progress`; the dev-mode `mcp_server_status` and `mcp_read_logs` tools bypass that guard.

See [Installation & Setup → First run](/guide/getting-started#first-run-metadata-sync) and the sync settings in the [Configuration Reference](/guide/configuration#metadata-sync).
