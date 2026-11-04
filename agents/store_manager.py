"""Builds the agent definition.

Pure by design: no network calls, no side effects. The definition is the agent's
whole contract - which model, what instructions, how hard it thinks, which tools
it may call. Keeping it in one function means the deploy script, the tests and
the eval suite all build the identical agent.
"""

from pathlib import Path

from azure.ai.projects.models import (
    AgentKind,
    PromptAgentDefinition,
    Reasoning,
    StructuredInputDefinition,
)

AGENT_NAME = "takealot-store-agent"

_REPO_ROOT = Path(__file__).resolve().parent.parent
INSTRUCTIONS_PATH = _REPO_ROOT / "instructions" / "store_manager.md"

# Store-wide policy. These are the only numbers that are global - per-product
# values (landed cost, minimum margin, reorder point) are never defined here;
# the agent reads those per product and asks the seller once when missing.
# PROVISIONAL defaults - replace with your real policy.
POLICY_INPUTS: dict[str, StructuredInputDefinition] = {
    "max_data_age": StructuredInputDefinition(
        description="Hours after which data is treated as stale and labelled as such.",
        default_value=24,
        schema={"type": "integer", "minimum": 1},
        required=False,
    ),
    "stockout_horizon_days": StructuredInputDefinition(
        description="How many days ahead to predict stock-outs.",
        default_value=21,
        schema={"type": "integer", "minimum": 1},
        required=False,
    ),
    "return_rate_threshold": StructuredInputDefinition(
        description="Return rate above which a product is flagged, as a fraction (0.05 = 5%).",
        default_value=0.05,
        schema={"type": "number", "minimum": 0, "maximum": 1},
        required=False,
    ),
}


def load_instructions() -> str:
    return INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def build_definition(model: str) -> PromptAgentDefinition:
    """Build the agent definition for a given model deployment."""
    return PromptAgentDefinition(
        kind=AgentKind.PROMPT,
        model=model,
        instructions=load_instructions(),
        # The diagnosis ladder is multi-step and order-sensitive. 'low' skips rungs.
        reasoning=Reasoning(effort="medium"),
        # Deliberately empty. Each tool gets designed when it is actually needed.
        # web_search was removed: it lets the agent satisfy the evidence rules
        # with figures from arbitrary web pages, which is worse than refusing.
        tools=[],
        structured_inputs=POLICY_INPUTS,
    )
