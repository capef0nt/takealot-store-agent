# Takealot Store Agent

A Python-based Azure AI Foundry project that models a single Takealot store manager as a strict, policy-aware agent. The goal is to automate the daily operating loop for a seller while keeping the system safe: no guesswork, no hidden actions, no unapproved writes, and every recommendation tied to evidence.

The project is designed for learning and portfolio use, and it maps directly to Azure AI-103 concepts around agent design, structured outputs, tool use, evaluation, and production-safe prompting.

## Why this project exists

This repo implements a store-management agent that:

- watches a Takealot seller account against active goals
- checks stock, product performance, pricing, and returns
- recommends actions with measurable evidence
- refuses unsafe or unsupported actions
- enforces strict JSON output contracts
- keeps the Foundry portal as a playground, while the repo remains the source of truth

The design decisions are captured in:

- `docs/superpowers/specs/2026-11-04-takealot-store-agent-design.md`

Read that document before changing the architecture or behaviour of the agent.

## Architectural overview

The design uses a single gated agent pattern:

- a Head / Store Manager agent reads business goals and daily store health
- department-style reasoning is represented through structured decision logic and proposals
- only the operations/execution layer is allowed to perform writes
- tiered authority guards the system:
  - Tier 0: read, compute, record, ask the seller
  - Tier 1: act then report (empty unless explicitly promoted)
  - Tier 2: recommend only; no buyer-visible or spend-related changes
- the model must return strict JSON according to a schema
- every answer is expected to reference a tool and a timestamp as evidence

This is intentionally more conservative than a free-form assistant. The core idea is not to produce clever text; it is to make the business decisions auditable and safe.

## Key implementation decisions

The repo follows a few important rules:

- Python + Microsoft Foundry
- SDK: `azure-ai-projects` 2.10.0
- authentication is keyless via `DefaultAzureCredential`
- never add a static API key to code or config
- deploy scripts are run as modules from the repo root: `python -m scripts.deploy_agents`
- the repo is the source of truth; portal edits are overwritten by the next deploy
- behavioural evals gate changes: `python -m scripts.run_evals` must pass before shipping

## Repository layout

```text
.
├── agents/
│   ├── client.py                 # One shared call path to the deployed agent
│   ├── store_manager.py          # Agent definition, instructions, JSON schema
│   └── store_manager.snapshot.json
├── docs/
│   └── superpowers/specs/
│       └── 2026-11-04-takealot-store-agent-design.md
├── evals/
│   ├── cases.jsonl               # Deterministic behavioural test cases
│   └── checks.py                 # JSON contract checks and eval logic
├── instructions/
│   └── store_manager.md          # Prompt/instructions for the agent
├── scripts/
│   ├── deploy_agents.py          # Creates a new version of the agent in Foundry
│   ├── run_agent.py              # Sends a single prompt to the agent
│   └── run_evals.py              # Runs the eval suite
├── .gitignore
├── CLAUDE.md                    # Project instructions for AI-assisted work
├── config.py                    # Runtime config loaded from environment variables
├── requirements.txt
├── README.md
└── test.py
```

## Prerequisites

- Python 3.11+
- Azure CLI installed and signed in locally
- access to an Azure AI Foundry project
- environment variables set for the Foundry endpoint and model deployment

## Local setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Authenticate with Azure:

```bash
az login
```

4. Set the required environment variables:

```bash
export FOUNDRY_PROJECT_ENDPOINT="https://<your-project>.services.ai.azure.com/api/projects/<your-project>"
export FOUNDRY_MODEL_DEPLOYMENT="<your-model-deployment-name>"
```

If the repo contains a local `.env`, it is loaded automatically by the scripts.

## Deploying the agent

Run from the repo root:

```bash
python -m scripts.deploy_agents
```

For a draft version used for evaluation before promotion:

```bash
python -m scripts.deploy_agents --draft
```

Important: the scripts must be run as modules from the repo root. Running them as files can break imports because `scripts/` is added to `sys.path` incorrectly.

## Running the agent

Send a prompt to the deployed agent:

```bash
python -m scripts.run_agent "should I drop the price on TAK-001?"
```

The runner expects a strict JSON reply from the agent and prints it in a readable format.

## Running the behavioural evaluations

Before a change is allowed to ship, the project must pass its deterministic checks:

```bash
python -m scripts.run_evals
```

You can validate the case file without calling the agent:

```bash
python -m scripts.run_evals --dry-run
```

You can run a single case:

```bash
python -m scripts.run_evals --case refuses_price_without_cost
```

The evaluation layer is intentionally deterministic: the checks parse the JSON output and enforce contract, authority, data-gap, and policy rules. The design notes explicitly say that when a case fails, the test should be made more precise rather than more lenient.

## The agent contract

The stored agent definition is built in `agents/store_manager.py` and includes:

- a strict JSON schema for output
- structured policy inputs such as `max_data_age`, `stockout_horizon_days`, and `return_rate_threshold`
- reasoning configuration
- a clean, empty tool list at the single-agent baseline
- instructions loaded from `instructions/store_manager.md`

This reinforces a major design principle: the agent contract is created in code in the repo and then deployed to Foundry, rather than edited casually in the portal.

## Safety and design principles

The system is designed around a few explicit principles:

- evidence before claims
- use tools, not memory, for numbers
- no action is claimed unless a tool returned it
- no pricing recommendation is allowed without a valid cost record
- no Tier 1 or unsafe writes are allowed without an explicit approval path
- the repo is the single source of truth for agent behaviour

## Project status

This repository is a working framework for a seller-facing AI store manager, with a single-agent implementation and eval-driven validation. The design file shows the intended evolution toward a multi-agent architecture with department-specific advisors and a dedicated execution gate.

## Related docs

- `docs/superpowers/specs/2026-11-04-takealot-store-agent-design.md`
- `instructions/store_manager.md`
- `evals/checks.py`
- `CLAUDE.md`

## License

This project does not currently declare a license in the repository snapshot provided here.
