# Installation & Setup

## Prerequisites

- **Node.js 20+** and **npm 10+**
- Network access to your Maximo instance
- The **`MAXMCPMETADATA`** automation script deployed in Maximo (mandatory — see below)

```bash
node -v   # must be >= 20
npm -v
```

## Step 1 — Deploy the `MAXMCPMETADATA` automation script

The metadata engine uses this script to extract object, attribute, and relationship metadata from Maximo.

- **Script name:** `MAXMCPMETADATA`
- **Source:** <https://raw.githubusercontent.com/soumyaprasadrana/maximo-mcp-server/refs/heads/main/MAXMCPMETADATA.py>

In Maximo:

1. **System Configuration → Platform Configuration → Automation Scripts**
2. Create a new script named `MAXMCPMETADATA`
3. Paste the content from the URL above
4. **Activate** the script

::: warning
Without this script the server still starts, but metadata sync fails and every tool returns `metadata_sync_in_progress`.
:::

## Step 2 — Install the server

```bash
npm install -g @soumyaprasadrana/maximo-mcp-server
```

Verify:

```bash
maximo-mcp-server --version
maximo-mcp-server --help
```

## Step 3 — Create persistent storage

The server keeps its metadata/OAuth database and logs on disk. Point these at persistent paths **outside** the Node working directory.

::: code-group

```bash [Linux / macOS]
mkdir -p /opt/maximo-mcp/data /opt/maximo-mcp/logs
```

```powershell [Windows]
New-Item -ItemType Directory -Force -Path C:\maximo-mcp, C:\maximo-mcp\data, C:\maximo-mcp\logs
```

:::

| Directory | Env var | Contents |
| --- | --- | --- |
| `<data-dir>/data/meta.db` | `MCP_DATA_BASE_DIR` | SQLite metadata + OAuth client database |
| `<logs-dir>/` | `MCP_LOGS_DIR` | Rolling log files (`mcp.YYYY-MM-DD.N.log`) |

## Step 4 — Start the server

Provide config via environment variables, CLI flags, or a `.env` file.

::: code-group

```bash [Env vars]
export MAXIMO_URL="https://your-maximo-host/maximo"
export MAXIMO_API_KEY="your-api-key"
export MCP_DATA_BASE_DIR="/opt/maximo-mcp"
export MCP_LOGS_DIR="/opt/maximo-mcp/logs"

maximo-mcp-server
```

```bash [CLI flags]
maximo-mcp-server \
  --maximo-url     "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key" \
  --data-dir       /opt/maximo-mcp \
  --logs-dir       /opt/maximo-mcp/logs
```

```dotenv [.env file]
MAXIMO_URL=https://your-maximo-host/maximo
MAXIMO_API_KEY=your-api-key
MCP_DATA_BASE_DIR=/opt/maximo-mcp
MCP_LOGS_DIR=/opt/maximo-mcp/logs
MCP_TRANSPORT=stdio
```

:::

Most agents (Claude Desktop, etc.) launch the server for you — see [Connecting Clients](/guide/clients).

## First run: metadata sync

On first startup the server downloads all Object Structure metadata. On large environments this takes **3–6 minutes**.

- **Resumable** — if interrupted, the next startup resumes from the last completed stage.
- **Persisted** — once complete, subsequent startups skip it.

| Stage | Fetches |
| --- | --- |
| 1. API metadata | List of all Object Structures (`/api/apimeta`) |
| 2. Schemas | JSON schema for each OS |
| 3. MBO metadata | Object/attribute/relationship data via `MAXMCPMETADATA` |

While sync runs, tool calls return `metadata_sync_in_progress` with the current stage and percentage. Start with `--dev-mode` and use `mcp_server_status` / `mcp_read_logs` to watch progress from inside the agent.

Sync startup modes:

| Mode | Flag | Behaviour |
| --- | --- | --- |
| Fire-and-forget (default) | *(none)* | Server starts immediately; sync runs in-process in the background |
| Synchronous | `--reconcile-sync` | Server blocks until sync completes before accepting connections |
| Background worker | `--bg-sync-worker` | Sync runs as a detached child process; a file lock prevents duplicates |

Next: the full [Configuration Reference](/guide/configuration).
