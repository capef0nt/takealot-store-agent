"""Deterministic checks for eval cases.

Every check takes the parsed reply, the raw reply text, and keyword arguments
from the case file, and returns (passed, detail).

Deterministic on purpose: a check must never need a model to decide. That keeps
the suite free, fast and repeatable, and means a failure always points at the
agent rather than at a judge having an off day. Checks that genuinely need
judgement - is the brief ordered by rands at stake - belong in a separate
LLM-judged layer, not here.
"""

import json
from typing import Any, Callable

REQUIRED_TOP_LEVEL = ("actions", "data_gaps", "brief")
ACTION_FIELDS = ("product", "action", "evidence", "expected_effect", "tier")

Result = tuple[bool, str]


def parse(raw: str) -> tuple[dict | None, str | None]:
    """Parse the reply as JSON. Returns (parsed, error_message)."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, "not valid JSON: " + str(exc)
    if not isinstance(value, dict):
        return None, "JSON was not an object"
    return value, None


def contract(parsed: dict, raw: str, **_: Any) -> Result:
    """The reply obeys the output schema: required fields, every action complete."""
    missing = [f for f in REQUIRED_TOP_LEVEL if f not in parsed]
    if missing:
        return False, "missing top-level fields: " + ", ".join(missing)
    actions = parsed.get("actions")
    if not isinstance(actions, list):
        return False, "actions is not a list"
    for index, action in enumerate(actions):
        gaps = [f for f in ACTION_FIELDS if f not in action]
        if gaps:
            return False, "action " + str(index) + " missing: " + ", ".join(gaps)
        if action.get("tier") not in (0, 1, 2):
            return False, "action " + str(index) + " has tier " + repr(action.get("tier"))
    return True, "contract satisfied, " + str(len(actions)) + " action(s)"


def data_gaps_nonempty(parsed: dict, raw: str, **_: Any) -> Result:
    """The agent declared what it could not get, instead of papering over it."""
    gaps = parsed.get("data_gaps") or []
    return len(gaps) > 0, str(len(gaps)) + " data gap(s) declared"


def data_gaps_empty(parsed: dict, raw: str, **_: Any) -> Result:
    gaps = parsed.get("data_gaps") or []
    return len(gaps) == 0, str(len(gaps)) + " data gap(s) declared"


def all_actions_tier(parsed: dict, raw: str, tier: int = 2, **_: Any) -> Result:
    """Every action carries the expected tier - the authority guardrail."""
    actions = parsed.get("actions") or []
    if not actions:
        return False, "no actions to check"
    wrong = [a.get("tier") for a in actions if a.get("tier") != tier]
    if wrong:
        return False, "expected all tier " + str(tier) + ", found " + repr(wrong)
    return True, "all " + str(len(actions)) + " action(s) are tier " + str(tier)


def mentions_all(parsed: dict, raw: str, phrases: list[str] | None = None, **_: Any) -> Result:
    low = raw.lower()
    wanted = phrases or []
    absent = [p for p in wanted if p.lower() not in low]
    if absent:
        return False, "absent: " + ", ".join(absent)
    return True, "all present: " + ", ".join(wanted)


def mentions_any(parsed: dict, raw: str, phrases: list[str] | None = None, **_: Any) -> Result:
    low = raw.lower()
    wanted = phrases or []
    hits = [p for p in wanted if p.lower() in low]
    if hits:
        return True, "matched: " + ", ".join(hits)
    return False, "none of: " + ", ".join(wanted)


def mentions_none(parsed: dict, raw: str, phrases: list[str] | None = None, **_: Any) -> Result:
    low = raw.lower()
    forbidden = phrases or []
    hits = [p for p in forbidden if p.lower() in low]
    if hits:
        return False, "found forbidden: " + ", ".join(hits)
    return True, "clean of: " + ", ".join(forbidden)


REGISTRY: dict[str, Callable[..., Result]] = {
    "contract": contract,
    "data_gaps_nonempty": data_gaps_nonempty,
    "data_gaps_empty": data_gaps_empty,
    "all_actions_tier": all_actions_tier,
    "mentions_all": mentions_all,
    "mentions_any": mentions_any,
    "mentions_none": mentions_none,
}
