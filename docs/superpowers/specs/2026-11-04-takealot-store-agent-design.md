# Takealot Store Agent - Design

Status: draft for review, revision 2
Date: 2026-11-04

## Intent

Running a Takealot store is a daily loop of small decisions: is every listing
live and buyable, what sold today, is stock going to last, are the ads earning
their cost, should a price move, are we actually making money. Sellers do this
by hand, and the costly mistakes - a stock-out, a price below margin, an ad
budget spent on a product that cannot ship - come from things nobody was
watching at the right moment.

This project is a **framework any Takealot seller can use** to run their store
toward their own goals. It is not tuned to one seller. Every goal, threshold,
keyword list, interval and seller-owned tool is configuration.

> **Tool intention:** let any Takealot seller run their store toward their own
> goals with less effort and fewer costly mistakes. It watches every function
> continuously, decides what matters most each day, and either acts within the
> authority the seller has granted or says clearly what to do and why.

Three purposes, in priority order:

1. A working framework that any Takealot seller can run their store with.
2. A portfolio artifact demonstrating production agent engineering.
3. Preparation for Microsoft exam AI-103 (Developing AI Apps and Agents on
   Azure). Its two largest domains - planning and managing an Azure AI solution
   (25-30%) and implementing generative AI and agentic solutions (30-35%) - are
   exercised directly, including orchestrated multi-agent solutions.

The store is accountable for profit, not revenue. A sale below the margin floor
is a loss.

## Design method

**Intention first.** Every level of the system is described by the same six
lines, each following from the one above:

1. Intention - why it exists
2. Optimises - the single outcome it pushes up
3. Protects - what it must never sacrifice
4. Sees - the information that intention requires
5. Decides - the levers it may pull
6. Builds - the capabilities that follow

If a capability cannot be traced back up to an intention, it is not built.

**Planning horizons.** Takealot moves fast, so the business layer is short:

| Horizon | Span | Status |
|---|---|---|
| Long term | 6-12 months | named, parked for now |
| Business layer | 1-3 months | where goals are set and steered |
| Weekly | 1 week | priorities and review |
| Daily | 1 day | monitoring and actions |

**Everything is measurable.** Goals at every level are SMART (see below), so the
performance of the store and of each agent can be measured, not interpreted.

## Goals

- Run a Takealot store's day-to-day operation for any seller, on a schedule.
- Steer every department toward SMART goals the seller sets.
- Keep stock available, accounting for the full replenishment timeline.
- Protect per-product profit; never price at or below the margin floor.
- Report financial health daily, weekly and monthly.
- Execute only through one gated agent, within authority the seller grants.
- Make every claim traceable to a tool call and a timestamp.
- Make every action measurable: expected effect recorded before, actual after.
- Gate every change to an agent on behavioural evals.

## Non-goals

Parked or excluded for this version. Several are deliberate "later" items.

- Not a dashboard. Output is a short brief with decisions in it.
- No product discovery or category gap searching. Separate, later work.
- No supplier ordering. Sellers' suppliers vary too much to generalise; the
  agent alerts the seller to reorder instead.
- No competitor stock sensing. It requires cart probing, which risks the
  account. Competitor *prices* are in scope.
- Not driving the Seller Portal UI for anything the Seller API can do.
- Not real-time. Scheduled runs are sufficient and far cheaper.
- Not covering the exam's computer vision, text analysis or information
  extraction domains. Considered and declined; studied separately.
- Not private-networked in its first life (see Decisions).

## Anti-goals

Things that make this a failure even if every feature works:

- It recommends or sets a price below the margin floor.
- It states a figure it did not receive from a tool.
- It spends money or changes something buyer-visible without approval.
- It gets a seller's account restricted or suspended.
- It needs babysitting - asks the same question every day because nothing it
  learns is persisted.
- Its eval suite is green but does not reflect real behaviour.
- Its agents cannot be measured, so nobody can tell whether they are helping.

## Constraints

- A framework, so nothing about a particular seller can be assumed: store size,
  suppliers, categories, goals, or which tools they own.
- SKU count is unbounded. A seller with fifteen hundred products cannot have
  every product reasoned over by a model on every run.
- Self-funded build; cost constrains architecture (no Azure AI Search Basic yet,
  no private endpoints in the first build).
- Python and Microsoft Foundry, `azure-ai-projects` 2.10.0, where the model is
  agent -> version -> session and agents are identified by name.
- The Takealot Seller API covers store actions; its exact surface is unverified
  until a discovery spike is run.
- The search results page has no API. The author's own ranking tool is one
  pluggable rank source; other sellers will not have it.
- The Courier Guy (TCG) is the inbound logistics integration.
- Region chosen for Foundry and model availability, not latency.

## Architecture: a head agent and four department agents

```
Seller  <->  Head agent                    goals in, brief and approvals out
                 |  asks
   Marketing - Supply chain - Finance      analyse, propose (read-only)
   Operations                              daily control tower status
                 |  proposals
             Head agent                    prioritise, settle trade-offs
                 |  approved actions
             Operations                    final checks, execute, record
```

**Head agent** at the business layer holds the goals, sets weekly priorities,
settles trade-offs between departments, and writes the daily brief.

**Four department agents**: Marketing, Supply chain, Operations, Finance.
Merchandising, customer matters and account health sit inside Operations.

**Operations is the only agent that executes.** Marketing, Supply chain and
Finance are read-only advisors that send structured proposals with evidence.
Operations validates each approved proposal - tier, approval, margin floor,
conflicts - then executes and records the outcome. Reasons:

- one gate: approval and tier rules enforced in one place, not four
- one audit trail of every change made to the store
- conflicts caught before execution (an ad boost meets a stock-out warning)
- least privilege: three agents hold no write tools, so cannot change anything
  however they are prompted
- simpler testing: advisor evals check recommendations, one executor eval checks
  safety

Risk: Operations becomes a bottleneck. Mitigation: its executor job is narrow -
validate, execute, record. The analysis stays with the proposing department.

**One voice.** Only the head agent talks to the seller.

**Proposals are the contract between agents.** A proposal is an item in the
`actions` schema already enforced on the agent's output. The JSON contract
built for the single agent becomes the contract between agents.

## SMART goals, cascaded

Goals are set by the seller and must be SMART:

| | Field |
|---|---|
| Specific | metric and scope (e.g. profit on category X) |
| Measurable | baseline and target |
| Attainable | checked against history, stock and cash |
| Realistic / relevant | linked to a long-term goal |
| Time-bound | deadline within 1-3 months |

The head agent rejects vague goals and asks the seller to sharpen them, flags
targets the data says are unrealistic, and tracks each goal as on track, at
risk or off track.

SMART cascades, each level linked to its parent:

```
Business goal (1-3 months)
  -> Department objective
      -> Weekly task
          -> Daily action
```

No weekly priority exists without a goal link.

**Consequence for the actions schema.** `expected_effect` is currently prose.
It becomes measurable fields: `goal_id`, `metric`, `expected_change`, `due`.
After execution Operations records the actual result; each weekly review
compares expected against actual. That gives each agent a measurable track
record - which is production evaluation of agent behaviour, an exam objective
in its own right.

## Head agent (business layer)

- **Intention:** steer the whole store toward the seller's 1-3 month goals.
- **Optimises:** progress against SMART goals.
- **Protects:** the margin floor and the approval rules - it cannot override
  Finance's floor or approve a Tier 2 action itself.
- **Sees:** goals, every department's status and proposals, results against
  expected effects.
- **Decides:** weekly priorities per department, the order of the daily brief,
  how cross-department conflicts are resolved.
- **Builds:** goal store with SMART validation, priority setting, conflict
  resolution, daily brief, weekly review.

Cadence: daily - run departments, collect proposals, prioritise, brief. Weekly -
review results against goals, set next week's priorities. Monthly - goal
check-in with the seller.

## Marketing

The marketing mix: product, price, place, promotion. Product discovery is out
of scope for this version.

- **Intention:** create profitable demand for the seller's products.
- **Optimises:** profitable sales growth, not traffic or ad metrics alone.
- **Protects:** margin (no demand bought at a loss) and the account.
- **Sees:** our products only - rank on their search terms, performance trend
  per product, reviews on our products - plus competitor prices.
- **Decides (proposes):** when a product needs a visibility boost through ads,
  deals or events; price suggestions from market conditions; listing content.
- **Builds:** rank tracking with a pluggable rank source, product performance
  trends, review reading, competitor price reading, promotion proposals, a
  margin-aware return-on-ad-spend check.

Core loop: rank or performance drops -> does the product need a promotion?

Pricing strategy is per product, set by the seller: **move fast** (lower price,
volume) or **hold margin** (fair price, slower). Marketing may suggest a switch -
for example a slow mover accumulating storage fees.

Return on ad spend only means something against margin: a product on 20% margin
needs at least 5x to break even on its ads. Finance supplies that bar.

## Supply chain

- **Intention:** never be out of stock - act early enough that stock is live in
  the DC before it runs out, with as little cash tied up as possible.
- **Optimises:** availability.
- **Protects:** cash (no overstock) and storage fees.
- **Sees:** stock per product per DC, sales velocity and days of cover,
  shipments in transit, historical lead times, working-day calendar.
- **Decides (proposes):** when to replenish, how much, which DC; alerts the
  seller to reorder from their supplier.
- **Builds:** stock-out prediction, reorder timing, overstock and ageing flags,
  lead-time learning, replenishment proposals.

Inbound flow:

```
1. Seller creates inbound shipment      (Takealot)
2. Seller books collection with TCG     (TCG)
3. TCG collects
4. Seller allocates delivery to TCG     (Takealot)
5. TCG delivers to DC in a booked slot
6. DC receives -> stock live
```

Whether steps 1 and 4 can be automated through the Seller API is unverified.

**The timing rule.** Work backwards from the predicted stock-out date:

```
predicted stock-out date
 - DC receiving        (delivered -> live and sellable)
 - DC slot wait        (starts after collection and allocation)
 - TCG transit
 - collection booking lead time
 - seller prep time
 - safety buffer       (wider over weekends, public holidays, peaks)
 = latest safe action date
```

The agent acts before the latest safe action date, not when stock runs low.
Days are working days. Lead times are learned from past shipments (booked ->
collected -> delivered -> live) rather than fixed. The seller's own supplier
time is a per-product configured input.

Measures: days out of stock, sales lost to stock-outs, shipments arriving late.

## Operations

The control tower and the execution arm. Includes merchandising, customer and
account health.

- **Intention:** keep the store running correctly - every listing live and
  accurate, every return handled, the account in good standing - and execute
  every approved change.
- **Optimises:** a store that is buyable and correct at all times.
- **Protects:** the seller's account standing.
- **Sees:** offer status (live, buyable, suppressed, errors), units sold today,
  listing quality, returns and reasons, account health metrics and notices;
  orders and SLAs only for sellers who ship orders themselves.
- **Decides:** whether a price change goes ahead; listing fixes; return
  handling; the task queue of portal work it handles or hands to the seller.
- **Builds:** the store control tower, the execution gate, write tools, the
  outcome recorder, the task queue.

Price decision flow:

```
Marketing   suggests a price from market conditions
Operations  checks margin with Finance and strategy fit with the head agent
            decides, executes (tier-gated), then monitors the effect:
            did it bring profit, or hurt margin?
```

Diagnosis ladder rungs 1 and 2 (buyable? suppressed?) belong here.

## Finance

- **Intention:** know the true profit of every product and the health of the
  business, and set the money limits the other agents work within.
- **Optimises:** profit.
- **Protects:** cash - never run out of money to restock or advertise.
- **Sees:** sales and Takealot fees per product, payouts received and pending,
  landed cost per product, ad spend, TCG costs, storage fees, return costs.
- **Decides (advises):** price floors, ad budget envelope, cash available for
  restock. May veto money-moving proposals; never executes.
- **Builds:** margin floor calculation, true profit per product, break-even
  return on ad spend, payout reconciliation, financial health reporting.

**The margin floor is a solve, not a sum.** Takealot's success fee differs by
category and is a percentage of the selling price, so:

    floor_price = (landed_cost + fixed_fees) / (1 - fee_pct - margin_pct)

- `fee_pct` - the product's category success fee, from a category fee table
  with a captured-on date
- `fixed_fees` - per-unit fixed costs, including that unit's share of the TCG
  inbound shipment cost
- `margin_pct` - minimum margin as a fraction of selling price; a rand-per-unit
  minimum moves into `fixed_fees` instead. Both forms are supported.
  [Assistant's call.]
- Periodic and account-level costs (storage, subscriptions) do not go into the
  floor; they are overhead in the health report.
- VAT is handled consistently: Takealot prices are VAT-inclusive, so landed
  cost is too.

Treated as a sum, the floor is systematically too low, and no deterministic
check would catch it because the check would share the wrong assumption.
Example: a true floor of R200 computes as R176, and the agent then advises
matching a competitor at R189.

If a product's category is unknown or the fee table is stale, the product is
not priced.

**Ground-truth gate:** no price recommendations ship until computed margin for
at least one real product reconciles against an actual Takealot payout.

Health report:

- daily: sales, profit, units sold
- weekly and monthly: profit and margin trend, costs by type (fees, ads, TCG,
  storage, returns)
- cash: payouts received, payouts pending, cash available for restock and ads

## Original capabilities, mapped

Nothing from the original ten capabilities is lost; each now has an owner.

| Capability | Owner |
|---|---|
| Inventory health | Supply chain |
| Stock-out prediction | Supply chain |
| Product performance | Marketing (trend), Operations (today's units) |
| Pricing | Marketing suggests, Finance floors, Operations decides |
| Search rank tracking | Marketing |
| Ad performance | Marketing proposes, Operations executes |
| Returns | Operations |
| Daily and weekly reports | Head agent (brief), Finance (health) |
| Weekly goals and tasks | Head agent |
| Replenishment booking | Supply chain proposes, Operations executes |
| Listing quality (recovered) | Operations |

## Decisions already taken, and why

**Keyless authentication from the first line of code.**
`DefaultAzureCredential` everywhere: `az login` locally, GitHub OIDC in CI,
managed identity in production - identical code in all three. Key-based local
auth is to be disabled so keyless is enforced, not intended.

**Public endpoint with IP restriction now; private networking deferred.**
Authentication and network reachability are separate axes. Private endpoints
cost money, need a VPN or jump host, and break GitHub-hosted CI runners. Stand
private networking up later as a short-lived exercise for the exam objective,
then tear it down.

**The repository is the source of truth; the Foundry portal is a playground.**
Nothing authored in the portal flows back into the repo. Portal edits are
overwritten by the next deploy.

**Every deploy creates a new agent version, stamped with its commit.**
`create_version` with `metadata={"commit": sha}` gives rollback, an audit trail
and traceability. `draft` stages a version for evaluation before promotion. The
deploy script warns on a dirty tree, because a version stamped with a commit
that does not contain its instructions is a lie.

**Authority is tiered, and enforced by tool inventory.**
Tier 0: read, compute, record, ask the seller for missing information. Tier 1:
act then report - deliberately empty until the seller promotes a capability.
Tier 2: recommend only - anything that spends money or is buyer-visible. The
tiers express intent; what enforces them is that only Operations holds write
tools, and only behind the approval gate.

**The output contract is a strict JSON schema.**
Every field required, `additionalProperties: false`. `data_gaps` gives refusals
a structured home so they can be tested. Rule: give every behaviour you care
about a field.

**Policy is configuration, split by global and per-product.**
Global values ride on Foundry `structured_inputs`, substituted at `{{name}}`.
Per-product values (landed cost, minimum margin, lead time) live in the state
store. In a framework, all of these are per-seller configuration with defaults.

**Missing per-product data is asked once, then stored.**
Prompting bootstraps data; it is never how data is read.

**A small state store.** Per-product records, store policy, rank history, the
category fee table, daily sales snapshots, goals, and the expected-versus-actual
action log. Azure Table Storage to begin; Cosmos DB is the scale answer.
Partitioned by seller, given the framework scope. [Assistant's call.]

**A deterministic pre-pass before the model.** Because SKU count is unbounded,
cover, reorder breaches, performance deltas and margin checks are computed in
plain code, and agents reason only over the exceptions. [Assistant's call,
following from the framework scope.]

**Tools execute client-side as function tools, at least to begin with.**
Injectable tool outputs are the only way an eval case can test grounded
behaviour rather than refusal. Cost: `ask()` becomes a tool-call loop.

**Evaluation has two layers.** Project-owned deterministic checks first, gating
every deploy; `azure-ai-evaluation` built-in evaluators second, once tools
return real data. Cases are JSONL and each names the rule it protects. With
multiple agents, each department gets its own cases, plus cases for the
Operations gate.

**When a case fails, make the check more precise - never more lenient**, except
when the rule itself changed underneath it.

**Instruction ambiguity shows up as output inconsistency.** When a case flips
between runs, suspect the instructions before the model.

**CI/CD is GitHub Actions, because Foundry has no CI.** Foundry provides
versions, drafts and an evaluation service, not orchestration. OIDC workload
identity federation, so no secret exists in the repository.

**Seller-owned tools are pluggable, never assumed.** The author's ranking tool
is one rank source. A custom MCP server wrapping Takealot and rank sources is
the portfolio flourish; the GA path carries the exam value.

## Current state

The single-agent framework is built and green:

- keyless auth verified against a live Foundry project
- agent definition built from the repo, with strict JSON output schema and
  structured inputs
- versioned deploy with commit provenance and a draft flag
- shared `ask()` for the runner and the eval suite
- three behavioural eval cases, stable at 3/3

What changes with this revision: the single `store_manager` agent becomes the
starting point for five agents. Its instructions will be split by department,
and two lines that assume competitor stock - diagnosis ladder rung 6 and "when
a rival is out of stock, consider raising" - are removed in that split.

## Deliberately left to the builder

- The Foundry mechanism for orchestration: connected agents, a workflow agent,
  or orchestration in code.
- The state store's concrete schema and partition keys.
- Each tool's function signature and JSON schema.
- How a draft version is promoted to live.
- The judged (LLM-graded) eval layer.
- Log and trace conventions beyond what the platform emits.
- When the project becomes an installable package.
- The Azure app registration and federated credential for CI, assumed not to
  exist yet. [Assistant's call.]

## Open questions

Only the author can answer these, and each changes the plan. Most important
first.

1. **Self-hosted per seller, or one hosted service for many sellers?** Decides
   auth (each seller's own Takealot token and Azure resources, or a shared
   service holding many sellers' tokens), state partitioning, onboarding and
   cost model.
2. **What the Seller API exposes.** To be answered by the discovery spike:
   sales history depth, offer and buy-box status, returns, DC stock, category
   fees, whether inbound shipments can be created and allocated to TCG, rate
   limits.
3. **The channel to the seller.** How the brief is delivered, how approvals come
   back, how goals are entered - for an unattended scheduled run.
4. **Whether ads data is reachable programmatically**, and if not, which
   fallback is acceptable.
5. **Rank sources for sellers without their own tool**, and whether the author's
   tool can run from Azure, given datacenter IPs are blocked faster than
   residential ones.
6. **What TCG's API supports**: booking, costs, tracking, and whether a sandbox
   exists for testing the one capability that spends money on logistics.
7. **A monthly cost ceiling per seller**, which decides storage and evaluation
   choices.
8. **Exam date**, and which wins when store needs and exam coverage conflict.
9. **Which capability earns Tier 1 first.**
10. **Default policy values** for the framework. The current 24 hours, 21 days
    and 0.05 are provisional placeholders chosen by the assistant.
