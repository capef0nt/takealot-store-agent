# Takealot Store Agent - Design

Status: draft for review
Date: 2026-11-04

## Intent

A single Takealot seller runs their store by hand. Each day they check listing
quality, adjust prices to stay competitive, look at ad performance, and work
through returns. When sales on a product go quiet, the diagnostic loop is
always the same: are the ads running, is the ad balance funded, and then - only
then - what has changed on the search results page, which competitors have
appeared, at what price, and who is out of stock.

This project turns that loop into an agent that operates the store against
goals the seller sets, rather than a dashboard the seller has to go and read.

Three purposes, in priority order:

1. Run the store. Real money, one real seller, daily use.
2. Serve as a portfolio artifact demonstrating production agent engineering.
3. Prepare for Microsoft exam AI-103 (Developing AI Apps and Agents on Azure),
   whose two largest domains - planning and managing an Azure AI solution
   (25-30%) and implementing generative AI and agentic solutions (30-35%) -
   this project exercises directly.

The seller is accountable for profit, not revenue. A sale below the margin
floor is a loss. That single fact shapes most of what follows.

## Goals

- Operate the store end to end on a schedule: inventory health, product
  performance, pricing, ads, search rank, returns, replenishment.
- Diagnose underperformance by a fixed ladder, cheapest internal checks before
  expensive external ones, and name which rung explained it.
- Protect per-product profitability. Never recommend a price at or below that
  product's margin floor, whatever competitors do.
- Predict stock-outs ahead of a configurable horizon and book replenishment.
- Track search-page rank over time at intervals the seller controls.
- Accept weekly strategic goals and track the tasks arising from them.
- Act only within authority the seller has explicitly granted; recommend
  everything else.
- Make every claim traceable to a tool call and a timestamp.
- Be demonstrably correct: behavioural evals gate every change to the agent.

## Non-goals

- Not a dashboard or BI tool. Output is a short brief with decisions in it.
- Not multi-tenant and not a product for other sellers. One store.
- Not an autonomous repricer. Pricing is a recommendation with margin impact
  stated in rands; the seller decides.
- Not covering the exam's computer vision, text analysis or information
  extraction domains. Those were considered and deliberately declined: the
  scope stretch would damage the project. They get studied separately.
- Not driving the Seller Portal UI for anything the Seller API can do.
- Not real-time. Scheduled batch runs are sufficient and far cheaper.
- Not private-networked in its first life (see Constraints).

## Anti-goals

Things that would make this a failure even if every feature worked:

- It recommends a price below the margin floor. Direct, quantifiable loss.
- It states a figure it did not receive from a tool. One fabricated number
  destroys the seller's trust in every number it produces.
- It spends money or changes something buyer-visible without approval.
- It gets the Takealot account restricted or suspended.
- It needs babysitting - asking the same question about the same product every
  morning because nothing it learns is persisted.
- Its eval suite is green but does not reflect real behaviour. A suite loosened
  to pass is worse than no suite, because it manufactures false confidence.

## Constraints

- Solo developer, self-funded. Cost materially constrains architecture: no
  Azure AI Search Basic tier yet, no private endpoints in the first build.
- Python and Microsoft Foundry. AI-103 targets Python and Foundry specifically,
  so this is both the exam-correct and the project-correct choice.
- `azure-ai-projects` 2.10.0. The agent model is agent -> version -> session,
  not the older agent/thread/run shape. Agents are identified by name.
- The Takealot Seller API covers store actions. Whether ads data is available
  programmatically is NOT yet verified and must be established before the ads
  capability is designed.
- The search results page has no API. The seller already owns working tooling
  that ranks listings as a buyer would see them. That tooling is wrapped, never
  rewritten; its shape is not yet known to this document.
- The Courier Guy API is the intended replenishment booking integration.
- Development venv is on Python 3.14. Azure SDK support at that version is new;
  3.12 is the safer floor if anything behaves oddly.
- Region must be chosen for Foundry and model availability, not latency. South
  Africa North is thin; Sweden Central or East US are the likely homes. A batch
  agent does not care about round-trip time to Johannesburg.

## Decisions already taken, and why

These are settled. The reasoning matters more than the choice, because the
reasoning is what tells a builder when a choice should be revisited.

**Keyless authentication from the first line of code.**
`DefaultAzureCredential` everywhere: `az login` locally, GitHub OIDC in CI,
managed identity in production - identical code in all three. Retrofitting
keyless auth means rewriting every call site, so it was never optional.
Key-based local auth is to be disabled on the resource so that keyless is
enforced rather than merely intended.

**Public endpoint with IP restriction now; private networking deferred.**
A public endpoint with local auth disabled still rejects the entire internet;
authentication and network reachability are separate axes. Private endpoints
cost money per endpoint, require a VPN or jump host for development, and break
GitHub-hosted CI runners entirely. Decision: keyless auth plus tight RBAC plus
IP-restricted public access now, and stand private networking up later as a
deliberately short-lived exercise for the exam objective - build it, understand
private DNS resolution, screenshot it, tear it down.

**The repository is the source of truth; the Foundry portal is a playground.**
Nothing authored in the portal flows back into the repo, and no integration
pulls it down. Instructions, definition, policy and tools live in git and are
pushed to Foundry by a script. Portal edits are experiments and will be
overwritten by the next deploy.

**Every deploy creates a new agent version, stamped with its commit.**
`create_version` rather than overwrite, with `metadata={"commit": sha}`. This
gives rollback, a complete audit trail of every instruction change, and the
ability to trace a bad answer back to the exact rules that produced it. The
`draft` flag exists so a version can be staged, evaluated, and only then
promoted. The deploy script warns on a dirty working tree, because a version
stamped with a commit that does not contain its instructions is a lie the
developer will later believe.

**A three-tier authority model, enforced by tool inventory rather than prose.**
Tier 0: read, compute, record, and ask the seller for missing information.
Tier 1: act then report - deliberately empty, and capabilities enter it only
when the seller promotes them one at a time. Tier 2: recommend only - anything
that spends money or is visible to buyers. The critical design point: the tiers
in the instructions express intent, but what actually constrains the agent is
which tools it has. An agent with no price-writing tool cannot change a price
however it is persuaded. Guardrails are architecture, not wording.

**The output contract is a strict JSON schema, not a prose request.**
Asked politely in prose for `actions` and `brief`, the agent returned markdown
with headings of its own invention - readable, unparseable. The definition now
carries a strict JSON schema with `additionalProperties: false` and every field
required, so the shape cannot be violated. A `data_gaps` field was added so
that refusals - the most important behaviour in the system - have a structured
home and can therefore be asserted by a test. General rule: give every
behaviour you care about a field, because behaviour with no field is behaviour
you cannot test.

**Policy numbers are split by whether they are global or per-product.**
Three are store-wide and ride on Foundry `structured_inputs`, substituted into
the instructions at `{{name}}` and changeable per invocation without touching
the prompt: stale-data threshold, stock-out horizon, return-rate threshold.
Two are inherently per-product and must never appear in instructions: the
margin floor and the reorder point. The margin floor is derived - landed cost
plus Takealot category fees plus that product's minimum margin - and the
reorder point is supplier lead time plus a buffer. No single number can stand
in for either.

**Missing per-product data is bootstrapped by asking once, then stored.**
When the agent meets a product with no cost record it asks the seller, records
the answer, and never asks again. Prompting is how data is bootstrapped, not
how it is read. Without persistence this becomes an anti-goal: an agent that
asks the same question every morning.

**One small state store, serving three jobs.**
A per-product record (landed cost, minimum margin, lead time, reorder point), a
single store-policy record, and rank history. Rank history is required because
a rank without yesterday's rank is meaningless. Recommendation: Azure Table
Storage to begin - rows are simple, it is part of a storage account, and it
costs pennies. Cosmos DB is the scale answer and is more exam-relevant, but it
is also what quietly consumes a self-funded subscription.

**Evaluation has two layers, and the deterministic layer comes first.**
Layer one is project-owned: deterministic Python checks over the structured
output, encoding this store's rules, free and repeatable, gating every deploy
by exit code. Layer two is `azure-ai-evaluation` with Foundry's built-in
evaluators for groundedness, relevance, safety and agent-specific qualities;
that layer matters most once real tools are returning real data to be grounded
in, and it carries direct exam weight. Cases are stored as JSONL because that
is the dataset format layer two consumes. Every case names the instruction rule
it protects, which is the audit trail from rule to test.

**When a case fails, make the check more precise - never more lenient.**
The one legitimate exception is when the rule itself has changed underneath the
check. This happened once already and is instructive: a check demanding every
action be Tier 2 became wrong the moment asking the seller for data was defined
as Tier 0. The fix was to assert the real invariants instead - that a Tier 2
recommendation is present, and that no action is ever Tier 1.

**Instruction ambiguity shows up as output inconsistency.**
When the same case passes and fails across runs, suspect the instructions
before the model. Three such holes were found and closed by exactly this
signal. This is the main reason the eval suite exists at this stage.

**CI/CD is GitHub Actions, because Foundry has no CI.**
Foundry provides deployment primitives - versions, the draft flag, a cloud
evaluation service - but not orchestration. The exam objective is worded
"integrate Foundry projects *with* CI/CD pipelines"; Foundry is the target, not
the engine. GitHub Actions is chosen over Azure DevOps only because the code is
already on GitHub. Authentication is OIDC workload identity federation, so no
secret exists in the repository: the three Azure identifiers are `vars`, not
`secrets`, because identifiers are not credentials.

**The seller's existing ranking tooling is wrapped, not rebuilt.**
It already solves the hardest data problem in the project - seeing the search
page as a buyer does - which no API provides. How it is wrapped (Azure
Function, container, or a custom MCP server) depends on what it is today.

**A custom MCP server is the portfolio flourish, not the foundation.**
Exam questions favour generally available features, so the GA path carries the
exam value. An MCP server wrapping the Takealot and ranking tools is the thing
that makes the repository memorable, and is reusable outside Foundry.

## Capability set

Ten capabilities were described by the seller. They are listed here as scope,
not as an order of work; ordering belongs in the implementation plan.

1. Inventory health - stock cover in days, items at or below reorder point.
2. Stock-out prediction within a configurable horizon.
3. Product performance against the prior comparable period.
4. Margin-aware competitive pricing recommendations.
5. Search-page rank tracking at seller-controlled intervals.
6. Ad performance, including whether ads are live and the balance funded.
7. Returns monitoring, including per-product return rate.
8. Daily and weekly reporting.
9. Weekly strategic goals set by the seller, with task tracking against them,
   either handled by the agent or raised as a recommended action.
10. Replenishment booking via the Courier Guy API.

Each capability's tools are designed when that capability is built, not
speculatively in advance. Tool design done ahead of need has consistently been
wrong.

## Current state

The framework is built and green.

- Keyless auth verified end to end against a live Foundry project.
- Agent definition built from the repo: instructions, reasoning effort,
  structured inputs, strict JSON output schema.
- Versioned deploy script with commit provenance and a draft flag.
- A shared `ask()` used by both the CLI runner and the eval suite.
- Three behavioural eval cases, stable at 3/3 across consecutive runs, each
  naming the rule it protects.
- The agent currently has no tools, so it correctly refuses almost everything
  and declares its data gaps. That is the evidence rules working, and it must
  not be "fixed" by loosening them.

## Deliberately left to the builder

- The state store's concrete schema, partition strategy and access module.
- The exact function signatures and JSON schemas of each tool.
- How weekly goals are captured and represented.
- The design of the judged (LLM-graded) eval layer.
- Log and trace field conventions beyond what the platform emits.
- Whether the project becomes an installable package. It will need to be when
  tests arrive; it is not required before then.

## Open questions

These change the plan, and only the seller can answer them.

1. Azure subscription type, because it decides whether Cosmos DB and Azure AI
   Search are affordable at all.
2. What the existing ranking tooling is - language, how it is invoked, what it
   returns, whether it keeps history, how it behaves when blocked.
3. The real policy numbers. The three global defaults currently in the
   definition - 24 hours, 21 days, 0.05 - are provisional placeholders chosen
   by the assistant, not by the seller.
4. Which capability earns Tier 1 first: the first thing the agent is trusted to
   do and report rather than recommend.
5. Whether ads data is reachable programmatically at all.
