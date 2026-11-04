"""Run behavioural eval cases against the deployed agent.

    python -m scripts.run_evals
    python -m scripts.run_evals --dry-run        # validate cases, call nothing
    python -m scripts.run_evals --case refuses_price_without_cost

Exits non-zero if any case fails, so CI can gate a deploy on it. That exit code
is the whole point: a prompt change that passes code review but fails a saved
case must not reach the live agent.
"""

import argparse
import json
import pathlib
import sys

from dotenv import load_dotenv

from evals import checks

CASES_PATH = pathlib.Path(__file__).resolve().parent.parent / "evals" / "cases.jsonl"

PASS = "PASS"
FAIL = "FAIL"


def load_cases(only: str | None = None) -> list[dict]:
    cases = [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if only:
        cases = [c for c in cases if c["id"] == only]
        if not cases:
            raise SystemExit("no case with id: " + only)
    return cases


def validate(cases: list[dict]) -> None:
    """Fail fast on a malformed case file rather than mid-run after paid calls."""
    seen: set[str] = set()
    for case in cases:
        for field in ("id", "rule", "prompt", "checks"):
            if field not in case:
                raise SystemExit("case missing " + field + ": " + repr(case)[:80])
        if case["id"] in seen:
            raise SystemExit("duplicate case id: " + case["id"])
        seen.add(case["id"])
        for chk in case["checks"]:
            if chk["name"] not in checks.REGISTRY:
                raise SystemExit("unknown check " + chk["name"] + " in case " + case["id"])


def run_case(case: dict, reply: str) -> tuple[bool, list[str]]:
    lines: list[str] = []
    parsed, parse_error = checks.parse(reply)
    if parse_error:
        return False, ["  " + FAIL + "  parse: " + parse_error]

    ok = True
    for chk in case["checks"]:
        fn = checks.REGISTRY[chk["name"]]
        try:
            passed, detail = fn(parsed, reply, **chk.get("args", {}))
        except Exception as exc:  # a broken check is a failure, not a crash
            passed, detail = False, "check raised " + type(exc).__name__ + ": " + str(exc)
        ok = ok and passed
        lines.append("  " + (PASS if passed else FAIL) + "  " + chk["name"] + ": " + detail)
    return ok, lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Run agent eval cases.")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate the case file without calling the agent")
    parser.add_argument("--case", help="run only the case with this id")
    args = parser.parse_args()

    cases = load_cases(args.case)
    validate(cases)

    if args.dry_run:
        print("validated " + str(len(cases)) + " case(s); no agent calls made")
        for case in cases:
            print("  " + case["id"] + " (" + str(len(case["checks"])) + " checks)")
        return 0

    load_dotenv(".env")
    from agents.client import ask  # imported late so --dry-run needs no credentials

    failures = 0
    for case in cases:
        print("\n" + case["id"])
        print("  rule: " + case["rule"])
        reply = ask(case["prompt"])
        ok, lines = run_case(case, reply)
        for line in lines:
            print(line)
        if not ok:
            failures += 1
            print("  ---- reply ----")
            print("  " + reply[:800].replace("\n", "\n  "))

    total = len(cases)
    print("\n" + str(total - failures) + "/" + str(total) + " cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
