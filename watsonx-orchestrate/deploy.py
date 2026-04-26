import os
import sys
import argparse
import subprocess


def run(cmd, fail=True):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0 and fail:
        print(f"[FAIL] Failed: {cmd}")
        sys.exit(1)


# -----------------------------
# MCP TEMPLATE PREP
# -----------------------------
def prepare_mcp(mcp_url):
    template = "mcp/maximo_mcp_remote.template.yaml"
    output = "mcp/maximo_mcp_remote.yaml"

    with open(template, "r") as f:
        content = f.read()

    content = content.replace(
        "https://<path-to-mcp-server>/mcp",
        mcp_url
    )

    with open(output, "w") as f:
        f.write(content)

    print(f"[OK] MCP config generated -> {output}")


# -----------------------------
# ENV SETUP
# -----------------------------
def setup_env(env, base_url, api_key):
    print("\nResetting environment...")

    run(f"orchestrate env remove -n {env}", fail=False)
    run(f"orchestrate env add -n {env} -u {base_url}")

    print("\nActivating environment...")
    run(f"orchestrate env activate --api-key {api_key} {env}")


# -----------------------------
# OAUTH SETUP (OPTIONAL)
# -----------------------------
def setup_oauth(client_id, client_secret, token_url, scope):
    if not client_id or not client_secret or not token_url:
        print("[INFO] Skipping OAuth setup (missing params)")
        return

    print("\nSetting OAuth credentials...")

    cmd = (
        "orchestrate connections set-credentials "
        "-a maximo_mcp_oauth "
        "--env draft --send-via body "
        f"--client-id \"{client_id}\" "
        f"--client-secret \"{client_secret}\" "
        f"--token-url \"{token_url}\" "
    )

    if scope:
        cmd += f"--scope \"{scope}\" "

    run(cmd)


# -----------------------------
# MAIN
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Maximo Orchestrate Deployment CLI")

    parser.add_argument("-env", help="Environment name")
    parser.add_argument("-apikey", help="Watsonx API Key")
    parser.add_argument("-url", help="Watsonx Base URL")
    parser.add_argument("-mcp-url", help="MCP Server URL")

    # OAuth params (optional)
    parser.add_argument("-client-id", help="OAuth Client ID")
    parser.add_argument("-client-secret", help="OAuth Client Secret")
    parser.add_argument("-token-url", help="OAuth Token URL")
    parser.add_argument("-scope", help="OAuth Scope")

    # Skip flags
    parser.add_argument("--skip-env", action="store_true")
    parser.add_argument("--skip-connection", action="store_true")
    parser.add_argument("--skip-oauth", action="store_true")
    parser.add_argument("--skip-mcp", action="store_true")
    parser.add_argument("--skip-agents", action="store_true")
    parser.add_argument("--skip-examples", action="store_true")

    args = parser.parse_args()

    # -----------------------------
    # ENV VAR FALLBACK
    # -----------------------------
    env = args.env or os.getenv("ORCH_ENV")
    api_key = args.apikey or os.getenv("ORCH_API_KEY")
    base_url = args.url or os.getenv("ORCH_BASE_URL", "https://api.watson-orchestrate.ibm.com")
    mcp_url = args.mcp_url or os.getenv("MCP_URL")

    client_id = args.client_id or os.getenv("OAUTH_CLIENT_ID")
    client_secret = args.client_secret or os.getenv("OAUTH_CLIENT_SECRET")
    token_url = args.token_url or os.getenv("OAUTH_TOKEN_URL")
    scope = args.scope or os.getenv("OAUTH_SCOPE")

    # -----------------------------
    # VALIDATION
    # -----------------------------
    if not env or not api_key:
        print("\n[FAIL] Missing required inputs")
        print("Required: -env, -apikey")
        sys.exit(1)

    if not args.skip_mcp and not mcp_url:
        print("\n[FAIL] MCP URL required unless --skip-mcp is used")
        sys.exit(1)

    # -----------------------------
    # EXECUTION
    # -----------------------------
    print("\nPreparing MCP toolkit...")
    if not args.skip_mcp:
        prepare_mcp(mcp_url)
    else:
        print("[SKIP] Skipping MCP preparation")

    # ENV
    if not args.skip_env:
        setup_env(env, base_url, api_key)
    else:
        print("\n[SKIP] Skipping env setup (using existing active env)")

    # CONNECTION
    if not args.skip_connection:
        print("\nImporting connection...")
        run("orchestrate connections import -f connections/maximo_mcp_oauth_connection.yaml")
    else:
        print("\n[SKIP] Skipping connection import")

    # OAUTH
    if not args.skip_oauth:
        setup_oauth(client_id, client_secret, token_url, scope)
    else:
        print("\n[SKIP] Skipping OAuth setup")

    # MCP TOOLKIT
    if not args.skip_mcp:
        print("\nImporting MCP toolkit...")
        run("orchestrate toolkits import -f mcp/maximo_mcp_remote.yaml")
    else:
        print("\n[SKIP] Skipping MCP toolkit import")

    # BASE AGENTS
    if not args.skip_agents:
        print("\nImporting base agents...")
        # Support agent
        run("orchestrate agents import -f agents/maximo_metadata_agent.yaml")
        # Core agents
        run("orchestrate agents import -f agents/maximo_read_agent.yaml")
        run("orchestrate agents import -f agents/maximo_create_agent.yaml")
        run("orchestrate agents import -f agents/maximo_update_agent.yaml")
        run("orchestrate agents import -f agents/maximo_status_agent.yaml")
        run("orchestrate agents import -f agents/maximo_workflow_agent.yaml")
    else:
        print("\n[SKIP] Skipping base agents")

    # EXAMPLES
    if not args.skip_examples:
        print("\nImporting example agents...")
        run("orchestrate agents import -f examples/maximo_wo_progress_analyzer.yaml")
        run("orchestrate agents import -f examples/maximo_asset_assistant.yaml")
        run("orchestrate agents import -f examples/maximo_storeroom_assistant.yaml")
        run("orchestrate agents import -f examples/example_read_sr_agent.yaml")
        run("orchestrate agents import -f examples/example_update_sr_agent.yaml")
        run("orchestrate agents import -f examples/example_create_sr_agent.yaml")
    else:
        print("\n[SKIP] Skipping example agents")

    print("\n[OK] Deployment completed successfully!")


if __name__ == "__main__":
    main()
