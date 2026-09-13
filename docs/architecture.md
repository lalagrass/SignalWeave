# Architecture

## Design principle

SignalWeave separates source material, neutral observations, and causal
interpretation so that each record can be revisited, and re-derived, without
exposing the original source.

```text
                         → interactive-agent bundle → local validation ┐
data/raw/ → direct API pipeline ────────────────────────────────────────┼→ data/inbox/ + data/private/ → export
                                                                         ┘
```

Both paths converge on the same validated private event, story, basket, and
run records. An interactive cloud agent is still a remote provider even though
the repository does not hold or use a project API key; its bundle records the
actual provider, model, and locality before local import.

Records are machine-authored and the review gate is pass-through
([ADR-0008](decisions/ADR-0008-machine-authored-records-and-pass-through-gate.md)):
nothing waits for a human, and everything is stamped `review_status: unreviewed`
with its `drafted_by` and run id. A story stays private until a promotion step
exists to de-identify it; nothing is published today.

## Storage zones

| Zone | Git status | Purpose |
| --- | --- | --- |
| `data/raw/` | ignored | Original transcripts and observed posts. |
| `data/inbox/` | ignored | Machine-proposed candidate event cards. |
| `data/private/` | ignored | Identity maps, private annotations, worklogs, run records, and private stories with their updates and baskets. Run records get their own fixed subfolder in milestone 2; add it to `public_check`'s allowed private-zone subfolders at the same time, or tracked docs cannot name it. |
| `data/reviewed/events/` | tracked when safe | Not yet implemented; de-identified records, introduced only when something needs to be published. |

Prompts and method files are **tracked**, under `methods/` at the repo root
(outside every `data/` zone so they are tracked by default), and must contain
no source text.

## Records

### Run

One file per pipeline run: model id, provider and locality
([ADR-0009](decisions/ADR-0009-model-provider-boundary.md)), method version,
input document id, and the verbatim model output. Immutable — re-running
produces a new run, never an overwrite. This is what makes a later model able to
redo the same input and be compared against what was produced before, so it
cannot be added retroactively.

### Candidate event

A proposed, neutral observation drawn from one source. It must include a stable
locator, the character span it cites, a dated summary, and uncertainty. The
cited span must verifiably exist in the source; that is the pipeline's only
content check.

### Story

A hypothesis about a mechanism, carrying groups, market sentiment, dated
updates, supporting and counter evidence, and open questions. It never stores a
price-derived verdict.

### Basket

The instruments a story implicates, in any market. It starts deliberately wide
and changes over time; membership changes are dated, carry a reason, and are
append-only. No weights, no ordering, no score.

## Modules

| Module | Responsibility | Status |
| --- | --- | --- |
| `public_check` | Prevent accidental publication of private material. | shipped |
| `schema` | Validate candidate event records. | shipped |
| `extract` | Segment private transcripts and enforce candidate boundaries. | shipped boundary |
| `review` | Append private keep, discard, or suggested-link decisions. | shipped, gate now pass-through |
| `threads` | Append evidence to stories. | shipped |
| `runs` | Record and re-read pipeline runs. | shipped |
| `basket` | Validate and store one story's instrument list. | shipped |
| `propose` | Model-backed candidate, story, and basket proposers behind the existing protocol. | shipped |
| `pipeline` | Deterministic orchestration: segment, propose, span check, story, basket. | shipped |
| `agent_bundle` | Validate and import a no-network interactive-agent bundle into the same private records. | shipped |
| `export` | Emit story and basket for layer 1. | shipped |
| `persona` | Derive evidence-backed research prompts from public corpus. | deferred |

## Boundaries

- SignalWeave never fetches a price, never ranks a story, never scores a basket.
  The export is the seam; MarketPulse consumes it, tracks relative strength, and
  renders the page.
- `run-pipeline` is the direct-provider route and requires separate source
  disclosure and cost authorization. `import-agent-bundle` makes no provider
  request; it validates a previously produced interactive-agent bundle locally.
- No command may print a number claiming a record is good. Cross-model agreement
  may route attention to disagreements; it may never be reported as a score.
- The pipeline is deterministic orchestration with model steps inside it, not an
  agent loop. Every step's input and output are storable, which is what makes a
  run re-runnable and comparable.
