"""Deploy the agent definition from this repo to Foundry.

Creates a NEW VERSION every run - it never overwrites. Each version is stamped
with the commit it came from, so any answer the agent gives can be traced back
to the exact instructions that produced it.

Run from the repo root:
    python -m scripts.deploy_agents
    python -m scripts.deploy_agents --draft
"""

import argparse
import subprocess
import sys

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agents.store_manager import AGENT_NAME, build_definition
from config import settings


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def git_dirty() -> bool:
    try:
        return bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--draft",
        action="store_true",
        help="stage the version for evaluation without making it the live one",
    )
    args = parser.parse_args()

    load_dotenv(".env")
    cfg = settings()

    sha = git_sha()
    if git_dirty():
        print(f"warning: working tree is dirty - version will be tagged {sha} but won't match it")

    client = AIProjectClient(
        endpoint=cfg.project_endpoint,
        credential=DefaultAzureCredential(),
    )

    version = client.agents.create_version(
        AGENT_NAME,
        definition=build_definition(cfg.model_deployment),
        description=f"deployed from {sha}",
        metadata={"commit": sha, "source": "repo"},
        draft=args.draft,
    )

    print(f"agent:   {AGENT_NAME}")
    print(f"version: {version.get('version')}")
    print(f"draft:   {bool(args.draft)}")
    print(f"commit:  {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
