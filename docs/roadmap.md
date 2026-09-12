# Roadmap

## Project state

**Current phase:** milestone 2 — first analysis, end to end, one page

Milestone 1 is complete: the loop closes. Candidate cards have a validated
schema, transcripts segment through a model-independent boundary, reviews and
threads are append-only, and a thread reads back deterministically.

**Plan revision, 2026-09-12.** The plan that milestone 1 was built against
assumed a human author for every free-text field, and gated an AI proposer on
twenty hand-written candidate summaries. There is no such human — the team is two
engineers — so that gate was a deadlock. Records are now machine-authored with a
pass-through review gate ([ADR-0008](decisions/ADR-0008-machine-authored-records-and-pass-through-gate.md)),
raw source may reach a model provider under recorded conditions
([ADR-0009](decisions/ADR-0009-model-provider-boundary.md)), and a basket starts
deliberately wide and is pruned over time rather than being filled precisely.

Every milestone below is accepted on something a reader can look at. Tests still
have to pass; they are not the deliverable.

**Last verified:** `uv sync --no-editable --reinstall-package signalweave`,
`uv run --no-sync pytest` (95 passed), and
`uv run --no-sync signalweave public-check` passed on 2026-09-12.

## Completed

- **Candidate event schema v0** — traceability and uncertainty required; a card
  cannot mark itself accepted.
- **Transcript extraction boundary v0** — in-memory segmentation, stable local
  locators, model-independent `CandidateProposer` protocol, no-write dry run.
- **Inbox review v0** — append-only `keep_unlinked` / `discard` /
  `link_to_thread` records that cannot mutate a thread.
- **Research threads v0** — human-owned threads with mechanism, open question,
  invalidation conditions and review date; dated append-only updates.
- **First walkthrough v0** — `draft-event`, `show-thread`,
  `list-threads --as-of`; the loop run once end to end on a real document.
  Three defects found in planning review and fixed (private path amended out of
  history, `public-check` gated on configuration, `drafted_by` split from
  ownership).

## Milestone 2: first analysis, end to end, one page

Transcript → story (groups, context, market sentiment) → a deliberately wide
basket → export → layer 1 tracks the basket → one page.

Everything machine-made, everything stamped `review_status: unreviewed`.

**Prerequisite, resolved 2026-09-12 in `docs/specs/milestone-2-v0.md`:** checked
directly against the MarketPulse repo rather than assumed. Basket-level RS
(`baskets.py`'s `compute_basket_metrics`/`_basket_rs`) already runs on an
arbitrary ticker list against the full `bars` pivot, which already covers every
listed common stock, not just `themes/v1.yaml`'s 65 tickers — not a blocker, as
long as this milestone doesn't lean on `either_way`'s theme-id resolution (it
doesn't; see "Basket shape" below).

Scope:

1. **Run record** — one file per run: model id, method version, verbatim output.
   No content addressing. This is the only part that cannot be added later: a run
   that was not recorded is gone. **Built** (`signalweave.runs`), synthetic tests
   only.
2. **Method files** — versioned prompts tracked in the repo, carrying no source
   text, so a method change is a reviewable patch. **Built** (`methods/`:
   `propose_v1.md`, `story_v1.md`, `basket_v1.md`).
3. **Pipeline** — segment → propose per segment → span check → story draft →
   basket. Deterministic orchestration with model steps inside it, not an agent
   loop; every step's input and output are storable, which is what makes a run
   re-runnable. **Built** (`signalweave.pipeline`, `signalweave.propose`); the
   proposer calls Anthropic (`ANTHROPIC_API_KEY`, never committed) — a real cost
   and a real ADR-0009 privacy consequence flagged for the PO, not defaulted to
   silently. A segment whose proposal fails the span-exists check is skipped,
   not fatal to the run.
4. **Pass-through gate** — every record carries `review_status: unreviewed`,
   `drafted_by`, and its run id, unconditionally. **Built** — enforced in
   `schema`, `threads`, and `basket`.
5. **Export** — story and basket, no price, no ranking. `export-baskets` as
   specified in `docs/specs/thread-exposure-v0.md`'s DO-2 command surface, with
   the one-basket-per-story shape from this spec's "Basket shape" section, not
   that file's superseded three-way split. **Built** (`signalweave.export`).
6. **The page** — rendered by MarketPulse, which owns price: story context, the
   basket, and the basket's relative strength, on one page. **Not built here** —
   a separate, later prompt once this export format is stable; MarketPulse's
   rendering is not this implementation's responsibility.

Also folded in, **built**: the three friction fixes from
`docs/specs/transcript-navigation-v0.md` (DO-3) — `--review-id` resolution
(path form still works), early `--thread` validation naming the unknown id
before any review-content check runs, `--help` documenting every repeatable
flag.

**Verification status, 2026-09-12:** items 1–5 and the friction fixes pass
`uv run --no-sync pytest` (95 passed, synthetic transcripts and a fake model
client only — no real API call made) and `uv run --no-sync signalweave
public-check`. **Not yet done:** an actual unattended run on one real
transcript, and item 6. Running the pipeline for real means spending money on
the Anthropic API and sending real source text to it (ADR-0009) — that run is
the PO's call to trigger, not something exercised automatically here.

**Acceptance (unchanged, not yet met):** the page exists, built unattended from
one real transcript, and a reader can say what story is being told and whether
the basket is strengthening. "Interesting" and "garbage" are both results.

## Milestone 3: the basket changes

Dated membership changes with reasons, visible history, and a dispersion flag —
a name behaving unlike the rest of its basket is surfaced to look at, never
judged and never ranked. A story whose basket and strength have both been
unchanged for several weeks is marked `parked`, reusing MarketPulse's existing
`stage` field rather than inventing a new one.

**Acceptance:** for one story, the basket has changed two episodes later, and the
page shows why.

## Milestone 4: second analysis — post lens

From an instrument in a post, infer several competing candidate themes, grow each
into its own story and basket, and track them side by side. Two candidates that
produce the same basket are the same story for tracking purposes and are merged —
if they cannot be told apart by basket, they cannot be told apart by strength.

**Acceptance:** one post grows at least two competing stories, and two weeks
later the page shows which is stronger.

## Milestone 5: third analysis — standing experiment slot

No completion date, deliberately. One experiment per cycle, referencing current
market and open-source practice, with no promised outcome.

First experiment: predict what the next episode will cover, then check against
the episode when it lands. It needs no investment expertise to score, the
feedback cycle is one week, and it measures the thing this analysis is actually
after — whether the pipeline has caught the story context being tracked.

The ceiling is worth stating: restating what a transcript said is not hard; a
professional eye is about what was *not* said, and there is no clean open-source
answer to that today.

## Deferred

Moved back until the pipeline is actually running, because until then there is no
evidence about whether they are needed:

- Method comparison harness (promptfoo), two-model diff, method scorecard.
- Turning the review gate from pass-through into a real gate — and then only on
  the steps that prove unreliable.
- `close-thread` outcome ceremony. Basket churn is the revisit action and it is
  continuous; a date-triggered close is not needed on top of it.
- Reviewed event promotion and de-identification. Trigger: a second person needs
  to read a record, or a record must leave the machine.
- Research persona. Prices inside SignalWeave. Ranking, weighting, automatic
  truth classification.

## Session handoff checklist

1. State the completed roadmap item and verification results.
2. Update this file's current phase and next scoped item.
3. Record durable architectural decisions under `docs/decisions/`.
4. Keep source-specific notes in ignored `data/private/worklog/`.
