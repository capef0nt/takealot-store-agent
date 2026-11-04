"""Builds the agent definition.

Pure by design: no network calls, no side effects. The definition is the agent's
whole contract - which model, what instructions, how hard it thinks, which tools
it may call, and what shape its answers must take. Keeping it in one function
means the deploy script, the runner and the eval suite all build the identical
agent. Assembled inline in a script instead, the evals would be testing
something that is not what you deployed.
"""

from pathlib import Path

from azure.ai.projects.models import (
    AgentKind,
    PromptAgentDefinition,
    PromptAgentDefinitionTextOptions,
    Reasoning,
    StructuredInputDefinition,
    TextResponseFormatJsonSchema,
)

AGENT_NAME = "takealot-store-agent"

_REPO_ROOT = Path(__file__).resolve().parent.parent
INSTRUCTIONS_PATH = _REPO_ROOT / "instructions" / "store_manager.md"

# Store-wide policy. These are the only numbers that are global - per-product
# values (landed cost, minimum margin, reorder point) are never defined here;
# the agent reads those per product and asks the seller once when missing.
# Substituted into the instructions wherever {{name}} appears.
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
        description="Return rate above which a product is flagged, as a fraction.",
        default_value=0.05,
        schema={"type": "number", "minimum": 0, "maximum": 1},
        required=False,
    ),
}

# The output contract, enforced structurally rather than requested politely.
# Every field is required and additionalProperties is false, which is what
# strict structured output demands: the model cannot omit a field or invent one.
OUTPUT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["actions", "data_gaps", "brief"],
    "properties": {
        "actions": {
            "type": "array",
            "description": "Recommended or taken actions. Empty when nothing needs doing.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["product", "action", "evidence", "expected_effect", "tier"],
                "properties": {
                    "product": {
                        "type": "string",
                        "description": "SKU or product name, or 'store' for store-wide actions.",
                    },
                    "action": {"type": "string"},
                    "evidence": {
                        "type": "string",
                        "description": "Tool and timestamp this rests on, or why it is absent.",
                    },
                    "expected_effect": {"type": "string"},
                    "tier": {
                        "type": "integer",
                        "enum": [0, 1, 2],
                        "description": "0 act freely, 1 act then report, 2 recommend only.",
                    },
                },
            },
        },
        "data_gaps": {
            "type": "array",
            "description": "Data needed and not obtained. Empty only if nothing was missing.",
            "items": {"type": "string"},
        },
        "brief": {
            "type": "string",
            "description": "Short prose for the seller, ordered by rands at stake.",
        },
    },
}


def load_instructions() -> str:
    return INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def build_definition(model: str) -> PromptAgentDefinition:
    """Build the agent definition for a given model deployment."""
    return PromptAgentDefinition(
        kind=AgentKind.PROMPT,
        model=model,
        instructions=load_instructions(),
        # The diagnosis ladder is multi-step and order-sensitive. low skips rungs.
        reasoning=Reasoning(effort="medium"),
        # Deliberately empty. Each tool gets designed when it is actually needed.
        # web_search was removed: it lets the agent satisfy the evidence rules
        # with figures from arbitrary web pages, which is worse than refusing.
        tools=[],
        structured_inputs=POLICY_INPUTS,
        text=PromptAgentDefinitionTextOptions(
            format=TextResponseFormatJsonSchema(
                name="store_manager_output",
                description="Actions, declared data gaps, and a seller-facing brief.",
                schema=OUTPUT_SCHEMA,
                strict=True,
            )
        ),
    )
