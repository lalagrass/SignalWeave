# Spec: thread exposure v0

**Milestone:** 2 — real material in, baskets out
**Roadmap item:** thread exposure v0 (follows transcript navigation v0)
**Appetite:** one session.
**Blocked on a PO decision:** see "The seam" below.

## Why

`docs/PRODUCT.md` lists Exposure as a core record — possible beneficiaries,
alternatives, constraints, and explicitly no composite score — and nothing
implements it. A thread today is prose with a review date. Prose cannot be
checked against anything. The stated product intent is that the story layer's
only output is a basket of instruments, and that the market, not the tool, is
the referee.

## The seam

Two repositories now model the same object: MarketPulse's narrative layer
already carries branches with three baskets, and SignalWeave carries threads.
Maintaining both means maintaining two schemas for one idea, and the usual
outcome is that neither is kept current.

Proposed split — **PO confirms before implementation**:

- SignalWeave is the only place a story is authored and reviewed. It owns
  events, threads, evidence, review dates, and baskets.
- MarketPulse consumes an exported basket and does what it is good at: tracking
  relative strength. It stops authoring narratives.
- SignalWeave never fetches a price, never ranks a thread, never scores a
  basket. The export is the boundary.

## DO-1 — exposure record

Add an exposure block to a thread, written by a human, append-only like the rest:

- `if_true` — instruments that benefit if the mechanism holds.
- `if_false` — instruments that benefit if the opposite side wins. This is the
  opposite-side beneficiary basket, not a "losers" list.
- `either_way` — shared upstream: instruments that benefit whichever side wins.

Rules: plain identifiers, any market, no weights, no ordering, no scores, no
counts compared between baskets. A basket may be empty and an empty basket is
a finding, not an error. `show-thread` prints the three baskets side by side
without commentary.

## DO-2 — export

```bash
uv run --no-sync signalweave export-baskets --as-of 2026-09-20 --out path/to/baskets.yaml
```

Emit one entry per thread: thread id, review date, overdue flag computed from
`--as-of`, and the three baskets. Nothing source-derived, no summaries, no
mechanism text — the export is a list of instruments, so it can cross into
another tool without carrying private research with it.

## Acceptance

1. Verification commands pass; tests use synthetic instruments only.
2. Every thread created during the transcript run gets its baskets filled by the
   reviewer, and at least one thread has an empty `if_false` — that emptiness is
   recorded in the worklog as a finding about the thread, not patched over.
3. The export is read successfully by the consuming tool in a throwaway script.
   Nothing is integrated in this item; the point is only to prove the contract
   survives the boundary.

## Out of scope

Price data, ranking, scoring, weighting, backtesting, any MarketPulse code
change, AI proposer, promotion, persona.
