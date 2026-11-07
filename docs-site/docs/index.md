---
layout: home

hero:
  name: "Maximo MCP Server"
  text: "Governed AI access to IBM Maximo"
  tagline: Agents look up the schema, stage every change, show a diff, and write to Maximo only after a human says yes.
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
  - title: Look up before you query
    details: Search Object Structures, fields and relationships first. os_query_builder turns intent into a validated query -- filters, child rows, timelines, saved queries and KPIs.
  - title: Stage, preview, then commit
    details: Every create, update and delete is staged in a Working Set and shown as a diff with validation warnings; nothing reaches Maximo until an explicit commit. Attachments upload after a plan-then-confirm step. Optionally survives restarts.
  - title: Answers, not just rows
    details: Group-by counts and sums computed by Maximo, valid values for any field (including table domains), BIRT reports as PDF, integration errors and the opt-in server log.
  - title: Status and workflow
    details: Status changes checked against Maximo's valid next statuses and electronic signatures; route workflow assignments and start processes -- each with a plan-then-confirm step.
  - title: Safe by design
    details: Every request pinned to your Maximo, read-only mode, per-user identity over HTTP, a built-in OAuth 2.0 server, tool-level disabling and optional audit logging. Maximo BMXAA errors come back verbatim.
  - title: Works with your client
    details: Claude, Cursor, Copilot Studio, watsonx Orchestrate (strict schemas) or any MCP client, over stdio or HTTP. One npm package, every tool, free for non-commercial use.
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
        "MCP_LOGS_DIR": "C:\\maximo-mcp\\logs",
        "MCP_RECONCILE_LAZY": "true"
      }
    }
  }
}
```

> One prerequisite: deploy the `MAXMCPMETADATA` automation script in Maximo. See [Installation & Setup](/guide/getting-started).

## The core loop

```
maximo_get_metadata   ->  discover the Object Structure and its fields
os_query_builder      ->  build a validated OSLC query (creates a Working Set)
ws_load               ->  pull records into the Working Set
ws_update_field / ... ->  stage changes (nothing sent to Maximo yet)
ws_preview_changes    ->  review a diff + non-blocking validation warnings
ws_commit             ->  apply -- Maximo is the final authority
```

Read [Introduction](/guide/introduction) for the why, or jump to the [Tool Reference](/tools/).
