---
layout: home

hero:
  name: "Maximo MCP Server"
  text: "Governed AI access to IBM Maximo"
  tagline: Metadata-aware query building and a staged Working Set transaction model — so agents read, reason, preview, and commit changes to Maximo safely.
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: What is it?
      link: /guide/introduction
    - theme: alt
      text: View on npm
      link: https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server

features:
  - icon: 🔎
    title: Metadata-aware discovery
    details: Semantic + keyword search over Object Structures, schemas, and child relationships. Agents discover the right fields before building a single query.
  - icon: 🧱
    title: Validated OSLC query builder
    details: os_query_builder turns structured intent into metadata-validated OSLC URLs — parent filters, child options, select, orderBy, saved queries.
  - icon: 📝
    title: Staged Working Set
    details: An in-memory transaction. Every create, update, and delete is staged, previewed with a diff, and only written on an explicit commit.
  - icon: 🧩
    title: First-class child records
    details: Add or remove one child row without resubmitting the whole array. Changes are diffed by natural key and tagged with per-row Maximo actions.
  - icon: 🔐
    title: Enterprise controls
    details: App-level permission gates, a built-in OAuth 2.0 server for HTTP transport, and optional append-only audit logging of every staged change.
  - icon: 🤖
    title: Client-ready
    details: Works with Claude Desktop over stdio and IBM watsonx Orchestrate via strict tool schemas. LEAN payload compression cuts tokens 40–60%.
---

## Install in 30 seconds

```bash
npm install -g @soumyaprasadrana/maximo-mcp-server
maximo-mcp-server --version
```

Then point your MCP client at it:

```json
{
  "mcpServers": {
    "maximo": {
      "command": "maximo-mcp-server",
      "env": {
        "MAXIMO_URL": "https://your-maximo-host/maximo",
        "MAXIMO_API_KEY": "your-api-key",
        "MCP_DATA_BASE_DIR": "C:\\maximo-mcp",
        "MCP_LOGS_DIR": "C:\\maximo-mcp\\logs"
      }
    }
  }
}
```

> One prerequisite: deploy the `MAXMCPMETADATA` automation script in Maximo. See [Installation & Setup](/guide/getting-started).

## The core loop

```
maximo_get_metadata   →  discover the Object Structure and its fields
os_query_builder      →  build a validated OSLC query (creates a Working Set)
ws_load               →  pull records into the Working Set
ws_update_field / …   →  stage changes (nothing sent to Maximo yet)
ws_preview_changes    →  review a diff + non-blocking validation warnings
ws_commit             →  apply — Maximo is the final authority
```

Read [Introduction](/guide/introduction) for the why, or jump to the [Tool Reference](/tools/).
