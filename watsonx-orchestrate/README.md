# IBM Watsonx Orchestrate + Maximo MCP Integration Guide

This guide provides step-by-step instructions to integrate the **Maximo MCP Server** with **IBM Watsonx Orchestrate** using a stateful, multi-agent architecture.

## What is This?

A production-ready orchestration layer that connects AI agents to IBM Maximo Application Suite through:

- **Multi-agent collaboration** — core agents own Maximo tools; process agents own business logic
- **Stateful session context** — thread-safe conversation memory across agent hops
- **Two-phase transaction lifecycle** — explicit prepare→preview→commit for data changes
- **Zero fabrication** — hard fail on errors; never invent business data

### Three Process Agents

1. **maximo_storeroom_assistant** — Fulfills inventory reservations with real-time balance enrichment and work order urgency comparison
2. **maximo_asset_assistant** — Manages asset lifecycle with flexible search and detail views
3. **maximo_wo_progress_analyzer** — Analyzes work order health, schedule risk, and labor tracking

---

## Prerequisites

Before you start, ensure you have:

- **Python 3.11+** (required for the Orchestrate ADK)

  ```bash
  python --version  # 3.11 or later
  ```

- **Node.js 20+** and **npm 10+** (for MCP server)

  ```bash
  node -v  # v20.x or later
  npm -v   # 10.x or later
  ```

- **IBM Watsonx Orchestrate ADK** (Agent Development Kit)

  ```bash
  pip install --upgrade ibm-watsonx-orchestrate
  ```

- **Network access** to your Maximo environment (on-premise or SaaS)

- **Maximo automation script** configured:
  - Script name: `MAXMCPMETADATA.py`
  - Source: `https://raw.githubusercontent.com/soumyaprasadrana/maximo-mcp-server/refs/heads/main/MAXMCPMETADATA.py`
  - This extracts Object Structure metadata required by the MCP Metadata Engine

- **IBM Watsonx Orchestrate** account with:
  - Service instance URL
  - API key

- **(For local development)** **ngrok** for exposing local MCP server
  ```bash
  ngrok --version  # Verify ngrok is installed
  ```
  Download: https://ngrok.com/download

---

## Step 1: Install MCP Server

### Option A: Global Install (Recommended)

```bash
npm install -g @soumyaprasadrana/maximo-mcp-server
```

Faster startup and avoids per-run package resolution delays.

### Option B: Local Install (npx)

```bash
npx -y @soumyaprasadrana/maximo-mcp-server@latest [options]
```

---

## Step 2: Set Up OAuth Client

**OAuth is provided by the MCP server itself** — this layer protects your MCP server when exposed over HTTP to Watsonx Orchestrate.

### Create OAuth Credentials (MCP Server)

Run this command once. The server will generate credentials and exit:

```bash
npx -y @soumyaprasadrana/maximo-mcp-server@latest \
  --data-dir /path/to/your/mcp-data \
  --setup-oauth \
  --oauth-client-id orchestrate-client \
  --oauth-scopes "read write delete"
```

**Output example:**

```
╔═══════════════════════════════════════════════════════════╗
║  OAuth Client Created                                     ║
║                                                           ║
║  Client ID:     orchestrate-client                        ║
║  Client Secret: aBc123DeF456gHi789jKl012mNo...            ║
║  Scopes:        read write delete                         ║
║                                                           ║
║  SAVE THESE CREDENTIALS — secret shown only once          ║
╚═══════════════════════════════════════════════════════════╝
```

**Important:**

- **Client ID is optional** — if `--oauth-client-id` is omitted, a random ID is auto-generated
- **You MUST save** both the Client ID and Client Secret
- If you lose the secret, it will be stored in `--oauth-creds-dir` (specified when starting MCP server)
- **Use the same data directory** (`--data-dir`) when starting the MCP server later

---

## Step 3: Start MCP Server for Watsonx Orchestrate

### Prepare Directories

**Create directories** (use paths of your choice, `/tmp` is just an example):

```bash
mkdir -p /path/to/your/mcp-data
mkdir -p /path/to/your/mcp-logs
mkdir -p /path/to/your/mcp-oauth
```

**Important:** The `--data-dir` must be **the same directory** you used in Step 2 when running `--setup-oauth`.

### Get Your Maximo API Key

Create an API key in your Maximo instance:

1. Log in to Maximo as administrator
2. Navigate to **System Configuration > API Keys**
3. Create a new key and save it (you'll need it below)

### Run MCP Server (HTTP Mode)

**Full command with all mandatory and optional flags:**

```bash
npx -y @soumyaprasadrana/maximo-mcp-server@latest \
  --data-dir /path/to/your/mcp-data \
  --logs-dir /path/to/your/mcp-logs \
  --oauth-creds-dir /path/to/your/mcp-oauth \
  --maximo-url http://YOUR_MAXIMO_HOST:9080/maximo \
  --maximo-api-key YOUR_MAXIMO_API_KEY \
  --transport http \
  --port 8001 \
  --strict-tool-schema \
  --log-to-console \
  --debug
```

**For production (without debug):**

```bash
npx -y @soumyaprasadrana/maximo-mcp-server@latest \
  --data-dir /path/to/your/mcp-data \
  --logs-dir /path/to/your/mcp-logs \
  --oauth-creds-dir /path/to/your/mcp-oauth \
  --maximo-url http://YOUR_MAXIMO_HOST:9080/maximo \
  --maximo-api-key YOUR_MAXIMO_API_KEY \
  --transport http \
  --port 8001 \
  --strict-tool-schema \
  --log-to-console
```

**Mandatory flags:**

- `--data-dir` — same directory from Step 2
- `--logs-dir` — directory for MCP logs
- `--maximo-url` — your Maximo instance URL
- `--maximo-api-key` — API key from your Maximo instance
- `--transport http` — required for Orchestrate
- `--port 8001` — or any available port
- `--strict-tool-schema` — required for Orchestrate; removes `anyOf:[type,null]` patterns that confuse the orchestrator

**Optional but recommended:**

- `--oauth-creds-dir` — stores OAuth credentials; if forgotten, retrieve from here
- `--log-to-console` — see live logs
- `--debug` — verbose logging (development only)

**Expected output:**

```
✓ MCP Server running on http://localhost:8001
✓ Metadata engine initialized
✓ Working Set store ready
✓ POST /mcp endpoint active
```

### Verify Server Health

```bash
curl http://localhost:8001/health
# Response: { "status": "ok", "version": "..." }
```

---

## Step 4: Expose MCP Server (Local Development)

If you're running MCP on your local machine, use **ngrok** to expose it publicly to Watsonx Orchestrate.

### Install ngrok

Download from https://ngrok.com/download and add to PATH.

### Expose Port 8001

In a new terminal:

```bash
ngrok http 8001
```

**Output example:**

```
ngrok by @inconshreveable

Session Status                online
Account                       (plan)
Version                       3.x.x
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://1234-56-789-012.ngrok-free.app -> http://localhost:8001

Connections                   ttl     opn     rt1     rt5     p50     p99
                              0       0       0.00    0.00    0.00    0.00
```

**Save the public URL:**

```bash
# bash / zsh (Linux / macOS)
export MCP_URL=https://1234-56-789-012.ngrok-free.app/mcp
```

```powershell
# PowerShell (Windows)
$env:MCP_URL="https://1234-56-789-012.ngrok-free.app/mcp"
```

---

## Step 5: Deploy Agents to Watsonx Orchestrate

**The deployment is handled by the Python `deploy.py` script**, which:

1. Sets up the Orchestrate environment
2. Registers the MCP connection
3. Deploys all agents

### Prerequisites for Deployment

Gather these values from your Watsonx Orchestrate console and from Step 2 (OAuth setup):

**Orchestrate credentials:**

| Variable        | Where to find                  | Example                                 |
| --------------- | ------------------------------ | --------------------------------------- |
| `ORCH_ENV`      | Environment name (you choose)  | `max-orchestrate`                       |
| `ORCH_API_KEY`  | API key from Orchestrate       | `your-api-key-here`                     |
| `ORCH_BASE_URL` | Service instance URL           | `https://YOUR_ORCHESTRATE_INSTANCE_URL` |
| `MCP_URL`       | Public URL from ngrok (Step 4) | `https://1234-abcd.ngrok-free.app/mcp`  |

**OAuth credentials (from Step 2 — MCP server's OAuth setup):**

| Variable              | Where to find                       | Example                                          |
| --------------------- | ----------------------------------- | ------------------------------------------------ |
| `OAUTH_CLIENT_ID`     | Printed when running `--setup-oauth` | `mcp-client-xxxxxxxxxxxxxxxx`                   |
| `OAUTH_CLIENT_SECRET` | Printed when running `--setup-oauth` | `your-client-secret-here`                       |
| `OAUTH_TOKEN_URL`     | Your MCP server's `/oauth/token`    | `https://YOUR_NGROK_URL/oauth/token`             |
| `OAUTH_SCOPE`         | Scopes you used in `--setup-oauth`  | `read write delete`                              |

### Set Environment Variables

Set these before running `deploy.py`, or pass them as inline CLI args (see below).

```bash
# bash / zsh (Linux / macOS)
export ORCH_ENV=your-environment-name
export ORCH_API_KEY=your-api-key
export ORCH_BASE_URL=https://YOUR_ORCHESTRATE_INSTANCE_URL
export MCP_URL=https://YOUR_NGROK_URL/mcp
export OAUTH_CLIENT_ID=your-client-id
export OAUTH_CLIENT_SECRET=your-client-secret
export OAUTH_TOKEN_URL=https://YOUR_NGROK_URL/oauth/token
export OAUTH_SCOPE="read write delete"
```

```powershell
# PowerShell (Windows)
$env:ORCH_ENV="your-environment-name"
$env:ORCH_API_KEY="your-api-key"
$env:ORCH_BASE_URL="https://YOUR_ORCHESTRATE_INSTANCE_URL"
$env:MCP_URL="https://YOUR_NGROK_URL/mcp"
$env:OAUTH_CLIENT_ID="your-client-id"
$env:OAUTH_CLIENT_SECRET="your-client-secret"
$env:OAUTH_TOKEN_URL="https://YOUR_NGROK_URL/oauth/token"
$env:OAUTH_SCOPE="read write delete"
```

### Run Deploy Script

**Option A — use environment variables (set above):**

```bash
cd watsonx-orchestrate
python deploy.py
```

`deploy.py` automatically reads all values from environment variables when no CLI args are supplied.

**Option B — pass values directly (platform-independent):**

```bash
cd watsonx-orchestrate

python deploy.py \
  -env YOUR_ENV \
  -apikey YOUR_API_KEY \
  -url https://YOUR_ORCHESTRATE_INSTANCE_URL \
  -mcp-url https://YOUR_NGROK_URL/mcp \
  -client-id YOUR_CLIENT_ID \
  -client-secret YOUR_CLIENT_SECRET \
  -token-url https://YOUR_NGROK_URL/oauth/token \
  -scope "read write delete"
```

**Skip flags (all optional):**

| Flag                | Effect                                           |
| ------------------- | ------------------------------------------------ |
| `--skip-env`        | Skip environment reset (use existing active env) |
| `--skip-connection` | Skip connection import                           |
| `--skip-oauth`      | Skip OAuth credential setup                      |
| `--skip-mcp`        | Skip MCP toolkit import                          |
| `--skip-agents`     | Skip core agent deployment                       |
| `--skip-examples`   | Skip example/process agent deployment            |

The script automatically deploys:

- MCP connection (maximo-mcp-remote)
- Core agents (metadata, read, create, update, status, workflow)
- Process agents (storeroom_assistant, asset_assistant, wo_progress_analyzer)
- Example agents (optional read, create, update examples)

### Verify Deployment

```bash
orchestrate agents list
```

Expected output shows all agents with status `deployed`.

---

## Step 6: Manual Agent Import (Alternative)

If you prefer to import agents individually:

```bash
cd watsonx-orchestrate

# Core agents first
orchestrate agents import -f agents/maximo_metadata_agent.yaml
orchestrate agents import -f agents/maximo_read_agent.yaml
orchestrate agents import -f agents/maximo_create_agent.yaml
orchestrate agents import -f agents/maximo_update_agent.yaml
orchestrate agents import -f agents/maximo_status_agent.yaml
orchestrate agents import -f agents/maximo_workflow_agent.yaml

# Process agents
orchestrate agents import -f examples/maximo_storeroom_assistant.yaml
orchestrate agents import -f examples/maximo_asset_assistant.yaml
orchestrate agents import -f examples/maximo_wo_progress_analyzer.yaml

# Example agents (optional)
orchestrate agents import -f examples/example_read_sr_agent.yaml
orchestrate agents import -f examples/example_create_sr_agent.yaml
orchestrate agents import -f examples/example_update_sr_agent.yaml
```

---

## Step 7: Cleanup (Remove Agents)

To remove all agents and reset the environment:

```bash
python cleanup.py \
  -env YOUR_ENV \
  -apikey YOUR_API_KEY \
  -url https://YOUR_ORCHESTRATE_INSTANCE_URL
```

Or, if environment variables are already set:

```bash
python cleanup.py
```

Or remove individual agents:

```bash
orchestrate agents delete maximo_storeroom_assistant
orchestrate agents delete maximo_asset_assistant
# ... etc
```

---

## Process Agents Overview

### 1. maximo_storeroom_assistant

**Purpose:** Fulfills inventory reservations from work orders with real-time balance enrichment and work order urgency comparison.

**Key Features:**

- Finds pending HARD/APHARD reservations
- Enriches with current inventory balance (on-hand, available)
- Compares two work orders to identify urgent needs
- Stages and commits inventory usage (issue) records
- Confirms with clerk before deducting stock

**Workflow:**

1. Show pending reservations (with balance enrichment)
2. Optionally compare two WOs for urgency
3. Select reservation(s) to fulfill
4. Preview and confirm
5. Commit issue record to Maximo

**Agents used:**

- `maximo_read_agent` (read reservations + inventory balances)
- `maximo_create_agent` (stage & commit issues)
- `maximo_wo_progress_analyzer` (compare work orders)

### 2. maximo_asset_assistant

**Purpose:** Search, view, and manage assets with flexible filtering and detail extraction.

**Key Features:**

- Search assets by name, site, location, or condition
- View asset details including maintenance history
- Edit asset fields (description, owner, status)
- Two-phase edit with preview & confirmation

**Agents used:**

- `maximo_read_agent` (asset search & details)
- `maximo_update_agent` (asset field updates)

### 3. maximo_wo_progress_analyzer

**Purpose:** Analyze work order health, schedule status, labor tracking, and risk flags.

**Key Features:**

- Retrieve full WO data (status, schedule, assignments)
- Analyze labor actuals vs planned
- Check worklog entries for progress evidence
- Flag risks (schedule slip, unassigned, zero labor)

**Agents used:**

- `maximo_read_agent` (WO details, worklog, assignments)

---

## Architecture Overview

### Layer Model

```
User / Watsonx Orchestrate UI
         |
         v
Process Agents (storeroom_assistant, asset_assistant, wo_progress_analyzer)
         |
    ctx_create/set/get/delete (Context Framework)
         |
         v
Core Agents (read_agent, create_agent, update_agent, status_agent, metadata_agent)
         |
    os_query_builder, ws_load, ws_commit, etc. (MCP Tools)
         |
         v
IBM Maximo REST / OSLC APIs (MXAPIINVRES, MXAPIINVUSE, MXAPIASSET, ...)
```

### Context Framework

All agent communication uses a **stateful session envelope**:

```json
{
  "session_id": "79530cc7-5633-43dc-a144-e9d115ea331b",
  "context": {
    "entity": "inventory",
    "osName": "MXAPIINVUSE",
    "objectName": "INVUSAGE",
    "request": { "siteid": "BEDFORD", "wonum": "1203" },
    "draft": { "wsId": "e537a9c2", "stage": "preview_shown" }
  },
  "task": {
    "request_type": "read|create|update",
    "phase": "prepare|commit"
  }
}
```

This enables:

- Thread-safe conversation memory
- Multi-turn transactions (prepare → preview → commit)
- Never losing user-provided values
- Explicit state machine lifecycle

### Sequence Example: Storeroom Assistant

See `examples/storeroom_assistant_sequence_diag_example.png` for a full flow diagram.

**Summary:**

1. User asks for pending reservations
2. Core Agent (storeroom_assistant) initializes context session
3. Read Agent fetches MXAPIINVRES (33 reservations)
4. Read Agent fetches MXAPIINVENTORY (balance enrichment)
5. Assistant displays table with status flags (OK, SHORT, OVER-RESERVED)
6. User requests WO comparison
7. WO Analyzer fetches both WO details via Read Agent
8. Assistant reports which WO is more urgent
9. User selects reservation to fulfill
10. Create Agent stages INVUSAGE draft
11. Preview shown to user
12. User confirms
13. Create Agent commits issue #1022 to Maximo
14. Session cleaned up; next task ready

---

## Environment Variables Reference

### Required for MCP Server

| Variable         | Description                   | Example                        |
| ---------------- | ----------------------------- | ------------------------------ |
| `MAXIMO_URL`     | Maximo REST endpoint          | `http://localhost:9080/maximo` |
| `MAXIMO_API_KEY` | Maximo API authentication key | `your-api-key-here`            |

### Optional for MCP Server

| Variable              | Default                   | Description                 |
| --------------------- | ------------------------- | --------------------------- |
| `MCP_TRANSPORT`       | `stdio`                   | `stdio` or `http`           |
| `MCP_SERVER_PORT`     | `8001`                    | HTTP server port            |
| `MCP_DATA_BASE_DIR`   | current working directory | SQLite metadata DB location |
| `MCP_OAUTH_CREDS_DIR` | none                      | OAuth credentials directory |
| `MCP_LOGS_DIR`        | logs/                     | Log file directory          |
| `MCP_LOG_TO_CONSOLE`  | false                     | Print logs to stdout        |
| `MCP_DEBUG`           | false                     | Enable debug logging        |

### Required for Orchestrate (`deploy.py`)

| Variable        | Description                  | Example                                 |
| --------------- | ---------------------------- | --------------------------------------- |
| `ORCH_ENV`      | Orchestrate environment name | `max-orchestrate`                       |
| `ORCH_API_KEY`  | Orchestrate API key          | `your-api-key`                          |
| `ORCH_BASE_URL` | Orchestrate API base URL     | `https://YOUR_ORCHESTRATE_INSTANCE_URL` |
| `MCP_URL`       | Public MCP server endpoint   | `https://1234-abcd.ngrok-free.app/mcp`  |

### Required for OAuth Setup (`deploy.py`)

These come from the MCP server's `--setup-oauth` output (Step 2).

| Variable              | Description                            | Example                                      |
| --------------------- | -------------------------------------- | -------------------------------------------- |
| `OAUTH_CLIENT_ID`     | OAuth client ID for MCP server         | `mcp-client-xxxxxxxxxxxxxxxx`                |
| `OAUTH_CLIENT_SECRET` | OAuth client secret for MCP server     | `your-client-secret-here`                    |
| `OAUTH_TOKEN_URL`     | Token endpoint on your MCP server      | `https://YOUR_NGROK_URL/oauth/token`         |
| `OAUTH_SCOPE`         | Space-separated list of allowed scopes | `read write delete`                          |

```bash
# bash / zsh
export ORCH_ENV=your-environment-name
export ORCH_API_KEY=your-api-key
export ORCH_BASE_URL=https://YOUR_ORCHESTRATE_INSTANCE_URL
export MCP_URL=https://YOUR_NGROK_URL/mcp
export OAUTH_CLIENT_ID=your-client-id
export OAUTH_CLIENT_SECRET=your-client-secret
export OAUTH_TOKEN_URL=https://YOUR_NGROK_URL/oauth/token
export OAUTH_SCOPE="read write delete"
```

```powershell
# PowerShell (Windows)
$env:ORCH_ENV="your-environment-name"
$env:ORCH_API_KEY="your-api-key"
$env:ORCH_BASE_URL="https://YOUR_ORCHESTRATE_INSTANCE_URL"
$env:MCP_URL="https://YOUR_NGROK_URL/mcp"
$env:OAUTH_CLIENT_ID="your-client-id"
$env:OAUTH_CLIENT_SECRET="your-client-secret"
$env:OAUTH_TOKEN_URL="https://YOUR_NGROK_URL/oauth/token"
$env:OAUTH_SCOPE="read write delete"
```

---

## Troubleshooting

### MCP Server won't start

**Issue:** `Error: Cannot connect to Maximo`

**Solution:**

- Verify `MAXIMO_URL` is reachable from your machine
- Check firewall/VPN access
- Confirm `MAXIMO_API_KEY` is valid
- Try with `--debug` flag to see detailed logs

### Agents fail to deploy

**Issue:** `401 Unauthorized` or `Invalid API key`

**Solution:**

- Verify `ORCH_API_KEY` is correct and has sufficient permissions
- Check your Watsonx Orchestrate account status
- If credentials are invalid, re-run deploy.py with correct values

### ngrok connection drops

**Issue:** MCP URL changes or connection timeout

**Solution:**

- Restart ngrok and update `MCP_URL` environment variable
- Use ngrok's `--authtoken` for persistence if you have a paid account
- Re-run deploy.py with new URL

### Agent says "osName not provided"

**Issue:** Process agent didn't seed context properly

**Solution:**

- Ensure `initial_context` in agent YAML includes `osNameHint` and `resolved.osName`
- Check `ctx_create` was called with correct entity type
- See `PROCESS_AGENT_TEMPLATE.md` for correct pattern

---

## Documentation Reference

- [MCP Server GitHub](https://github.com/soumyaprasadrana/maximo-mcp-server)
- [AGENT_ARCHITECTURE.md](./AGENT_ARCHITECTURE.md) — Multi-agent design patterns
- [AGENT_CONTEXT_PATTERN.md](./AGENT_CONTEXT_PATTERN.md) — Context framework specification
- [PROCESS_AGENT_TEMPLATE.md](./PROCESS_AGENT_TEMPLATE.md) — Build custom process agents

---

## License & Support

For issues, feature requests, or contributions, visit the [GitHub repository](https://github.com/soumyaprasadrana/maximo-mcp-server).
