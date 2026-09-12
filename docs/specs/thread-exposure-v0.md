> **Folded into milestone 2 on 2026-09-12; not implemented as a standalone item.**
> The seam decision below stands and is unchanged. The basket shape does not: a
> basket now starts deliberately wide rather than being filled precisely, and
> membership changes over time with dated reasons. `export-baskets` survives as
> specified. Acceptance criterion 2 (the reviewer fills every basket) is void —
> baskets are machine-drafted under ADR-0008.

# Spec: thread exposure v0

**Milestone:** 2 — real material in, baskets out
**Roadmap item:** thread exposure v0 (follows transcript navigation v0)
**Appetite:** one session.

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

The split is decided. This is the rule, not a proposal:

- SignalWeave is the only place a story is authored and reviewed. It owns
  events, threads, evidence, review dates, and baskets.
- MarketPulse consumes an exported basket and does what it is good at: tracking
  relative strength. It stops authoring narratives.
- SignalWeave never fetches a price, never ranks a thread, never scores a
  basket. The export is the boundary.

This settles authorship and the shape of the boundary. It does not obligate
this item to touch MarketPulse's code, retire its narrative layer, or migrate
any of its existing branches — that migration is separate work, on
MarketPulse's side, done after this export exists and is proven readable. See
"Not part of this spec's acceptance" below.

## DO-1 — exposure record

> **Superseded for M2 by `docs/specs/milestone-2-v0.md`'s "Basket shape"
> section.** That spec picks one basket per story — a flat instrument list,
> machine-drafted, no split — over the three-way `if_true`/`if_false`/
> `either_way` design below, and gives its own reasoning (it matches the docs
> actually rewritten for this redesign, and "possibly related, wide" is not a
> claim split into two sides of a bet). The design below is not built; it is
> kept only as the record of what M1-era thinking proposed before the pivot.

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

> For M2, "the three baskets" below is one basket: a flat instrument list, per
> `docs/specs/milestone-2-v0.md`. The command surface (`--as-of`, `--out`,
> thread/story id, review date, overdue flag) is what survives from this DO-2;
> the payload shape does not.

Emit one entry per thread: thread id, review date, overdue flag computed from
`--as-of`, and the three baskets. Nothing source-derived, no summaries, no
mechanism text — the export is a list of instruments, so it can cross into
another tool without carrying private research with it.

## Acceptance

> Superseded for M2 by `docs/specs/milestone-2-v0.md`'s own Acceptance section.
> The "three baskets" and "if_false" wording in items 2–3 below refers to the
> superseded DO-1 shape and no longer describes what M2 tests.

Acceptance for this spec is synthetic only. It is done when:

1. Verification commands pass (`uv run --no-sync pytest`,
   `uv run --no-sync signalweave public-check`); tests use synthetic threads
   and synthetic instrument identifiers only — no real thread and no real
   instrument is required.
2. Tests cover an empty basket on synthetic data (e.g. an empty `if_false`)
   passing validation and printing as a finding, not an error, and confirm no
   weight, order, count, or score can be attached to a basket.
3. A throwaway script — not part of the package, not committed, run once and
   discarded — reads the export written by `export-baskets` on synthetic data
   and confirms it can get thread id, review date, overdue flag, and all three
   baskets out of it without any SignalWeave code. This proves the contract
   survives the boundary; it is not an integration.

## Not part of this spec's acceptance

Filling in real baskets on threads from the PO's own real-transcript
walkthrough, and any work on MarketPulse's side — retiring its narrative
layer, migrating existing branches to consume this export, wiring the export
into its relative-strength tracking — are separate follow-up work, not this
item. This item ships when the export format exists, is documented, and is
provably readable by an outside script; what MarketPulse does with it next is
out of scope here.

## Out of scope

Price data, ranking, scoring, weighting, backtesting, any MarketPulse code
change, AI proposer, promotion, persona.
