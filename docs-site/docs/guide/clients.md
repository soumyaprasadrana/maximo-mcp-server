# Connecting Clients

The server supports two transports: **stdio** (the client launches the process) and **http** (a long-running service, protected by OAuth 2.0).

## Claude Desktop (stdio)

Add the server to `claude_desktop_config.json`:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

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

Restart Claude Desktop after saving.

To let metadata sync run without blocking the first conversation, add `"MCP_BG_SYNC_WORKER": "true"` — sync runs as a detached process and a file lock prevents duplicate workers on restart.

## IBM watsonx Orchestrate

Orchestrate requires JSON Schemas without `anyOf`/`oneOf`. Set `MCP_STRICT_TOOL_SCHEMA=true` to switch every tool to its strict, flat, string-only schema variant.

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
        "MCP_STRICT_TOOL_SCHEMA": "true"
      }
    }
  }
}
```

For HTTP transport with Orchestrate, also configure OAuth (below).

## Any MCP client with the Inspector

Test tools interactively with the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector maximo-mcp-server
```

## HTTP transport with OAuth 2.0

When `MCP_TRANSPORT=http`, the server enforces OAuth 2.0 Bearer authentication on all MCP connections. Clients use the `client_credentials` grant to obtain a signed JWT.

### 1. Create an OAuth client

```bash
maximo-mcp-server \
  --setup-oauth \
  --data-dir /opt/maximo-mcp \
  --maximo-url "https://your-maximo-host/maximo" \
  --maximo-api-key "your-api-key"
```

This prints `client_id` and `client_secret`.

::: danger Save the secret
The secret is shown **only once** and is stored hashed — it cannot be recovered. If lost, delete the client and create a new one. If `MCP_OAUTH_CREDS_DIR` is set, the credentials are also written to `oauth-credentials.json` there.
:::

### 2. Obtain a token

```bash
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=<your-client-id>" \
  -d "client_secret=<your-client-secret>"
```

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 3. Connect

Send `Authorization: Bearer <access_token>` on every MCP HTTP request.

### Managing clients

```bash
# List registered clients (secrets not shown)
maximo-mcp-server --list-oauth-clients --data-dir /opt/maximo-mcp \
  --maximo-url "..." --maximo-api-key "..."

# Remove a client
maximo-mcp-server --delete-oauth-client <client-id> --data-dir /opt/maximo-mcp \
  --maximo-url "..." --maximo-api-key "..."
```

See the OAuth environment variables in the [Configuration Reference](/guide/configuration#oauth-2-0-http-transport).
