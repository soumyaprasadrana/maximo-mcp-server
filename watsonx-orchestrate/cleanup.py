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


def main():
    parser = argparse.ArgumentParser(description="Maximo Orchestrate cleanup CLI")
    parser.add_argument("-env", help="Environment name")
    parser.add_argument("-apikey", help="Watsonx API key")
    parser.add_argument("-url", help="Watsonx base URL")
    args = parser.parse_args()

    env = args.env or os.getenv("ORCH_ENV")
    api_key = args.apikey or os.getenv("ORCH_API_KEY")
    base_url = args.url or os.getenv("ORCH_BASE_URL", "https://api.watson-orchestrate.ibm.com")

    if not env or not api_key:
        print("\n Missing required inputs")
        print("Required: -env, -apikey")
        sys.exit(1)


    print("\n Activating environment...")
    run(f"orchestrate env add -n {env} -u {base_url}", fail=False)
    run(f"orchestrate env activate --api-key {api_key} {env}")

    print("\n Removing agents...")
    for agent_name in [
        "maximo_wo_progress_analyzer",
        "maximo_asset_assistant",
        "maximo_storeroom_assistant",
        "example_read_sr_agent",
        "example_update_sr_agent",
        "example_create_sr_agent",
        "maximo_read_agent",
        "maximo_create_agent",
        "maximo_update_agent",
        "maximo_status_agent",
        "maximo_workflow_agent",
        "maximo_metadata_agent",
    ]:
        run(f"orchestrate agents remove -n {agent_name} -k native", fail=False)

    print("\n Removing toolkit...")
    run("orchestrate toolkits remove -n maximo_mcp_remote", fail=False)

    print("\n Removing connection...")
    run("orchestrate connections remove -a maximo_mcp_oauth", fail=False)

    print("\n Removing environment...")
    run(f"orchestrate env remove -n {env}", fail=False)

    print("\n Cleanup completed.")


if __name__ == "__main__":
    main()
