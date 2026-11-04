"""Send one prompt to the deployed agent.

Run from the repo root:
    python -m scripts.run_agent "should I drop the price on TAK-001?"
"""

import argparse
import json
import sys

from dotenv import load_dotenv

from agents.client import ask


def main() -> int:
    parser = argparse.ArgumentParser(description="Send one prompt to the agent.")
    parser.add_argument("prompt", nargs="+", help="what to ask the agent")
    parser.add_argument("--raw", action="store_true", help="print the reply unformatted")
    args = parser.parse_args()

    load_dotenv(".env")
    reply = ask(" ".join(args.prompt))

    if args.raw:
        print(reply)
        return 0

    # The agent is under a strict JSON schema, so this should always parse.
    # If it does not, that is itself the finding: print it and fail.
    try:
        print(json.dumps(json.loads(reply), indent=2))
    except json.JSONDecodeError as exc:
        print("reply was not valid JSON (" + str(exc) + "):", file=sys.stderr)
        print(reply, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
