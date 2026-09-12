# Spec: milestone 2 — one page

**Milestone:** 2 — first analysis, end to end, one page
**Governing plan:** `docs/roadmap.md` (v4, 2026-09-12), `docs/PRODUCT.md`, `docs/architecture.md`, ADR-0008, ADR-0009.
**Supersedes, for M2 purposes:** `docs/specs/transcript-navigation-v0.md` (retired — DO-3 folded in below) and `docs/specs/thread-exposure-v0.md` (folded in — DO-2's export command contract survives, DO-1's basket shape does not; see "Basket shape" below).

## Why

Milestone 1 assumed a human wrote every free-text field and gated an AI proposer on twenty hand-written examples. There is no such human. ADR-0008 makes records machine-authored with a pass-through gate; ADR-0009 allows raw source to reach a remote model provider, recorded per run. The method is: start a basket deliberately wide, prune it later on what later sources, earnings, and the basket's own internal behavior say. This spec is what M2 actually builds under that method.

## Resolved before writing this: the MarketPulse prerequisite

The roadmap flagged an open question: can MarketPulse's layer 1 compute relative strength for tickers outside `themes/v1.yaml`? Checked directly against the MarketPulse repo rather than assumed:

- **Raw data ingestion already covers the whole market.** `marketpulse/data.py` (`parse_twse_payload`, `parse_tpex_payload`) parses the full daily TWSE/TPEx quote table and filters only by `is_listed_common` (four-digit code, not an ETF or TDR) — not by theme membership. Every listed common stock is already in `bars`, whether or not it's one of the 65 tickers in `themes/v1.yaml`.
- **Basket-level RS already runs on an arbitrary ticker list.** `marketpulse/baskets.py`'s `compute_basket_metrics` / `_basket_rs` computes `mean(member return_k) − TAIEX return_k` directly against the `close` pivot built from `bars`. This is exactly how the existing `if_true` and `if_false` baskets work today — `narratives.py`'s own comment confirms it: "the other two hold symbols." No `ThemeSet`, no code change.
- **The one thing that is theme-bound:** `either_way`, which today is declared as a list of `theme_id`s and resolved to member tickers via `ThemeSet.by_id()` (`baskets.py`'s `resolve_either_way`; `narratives.py`: "`either_way` holds theme_ids... theme membership is frozen"). That's a deliberate choice for the old if-true/if-false/either-way thesis-branch model (sprint 014), not a limit of the RS math.

**Conclusion: not a blocker.** A wide basket of arbitrary tickers gets an RS number today with zero MarketPulse code change, as long as M2 doesn't lean on `either_way`'s theme-id resolution. See "Basket shape" below for why M2 shouldn't.

## A second thing found while checking the first: the basket shape isn't settled

`docs/specs/thread-exposure-v0.md`'s DO-1 still describes sprint 014's three-way split (`if_true` / `if_false` / `either_way`), written as if a human still fills it by hand — that's stale text sitting under its own "folded into M2, machine-drafted" preamble note. `docs/PRODUCT.md` and `docs/architecture.md`, both actually rewritten for v4, describe one basket per story: "the instruments a story implicates," no if-true/if-false framing anywhere.

These are two different shapes. This spec picks one:

**One basket per story.** It matches the docs actually written for this redesign (not carried over from the old model), needs no `ThemeSet`, and fits the method — "possibly related, wide" is not a claim split into two sides of a bet. The if_true/if_false/either_way frame belongs to the thesis-branch model this milestone is explicitly moving away from (see ADR-0008: "is this card correct" is not the question this product answers — and neither is "which side of the bet does this name belong to").

`docs/specs/thread-exposure-v0.md`'s DO-1 is superseded by this section for M2. If a later milestone wants a shared-upstream split back (M4's "two candidate stories that produce the same basket are merged" logic might want one), that's a decision to make then, with its own reasoning — not something to half-restore now.

## Open item this spec cannot resolve alone: which model provider

`pyproject.toml` has no AI SDK dependency at all today — `PyYAML` and `pytest` only. ADR-0009 permits a remote provider and requires every run to record `provider`, `model_id`, `model_locality`, but does not pick one. Building `propose` means adding a real dependency and, almost certainly, a credential (an API key read from environment, never committed — `public_check`'s existing rules already forbid source text in tracked files, and a key is a different, additional thing to keep out).

Recommendation, not a silent default: use the Anthropic API — it's the ecosystem the rest of this tooling already runs in, and ADR-0009's `model_locality: remote` tier fits it directly. But this spends the PO's money on every run and reads private material out to a third party per source's privacy tier, so it goes in the implementing prompt as something to confirm on the first real run, not something to bury in code.

## Scope

1. **Run record.** New folder `data/private/runs/`, one file per pipeline run: `model_id`, `provider`, `model_locality` (ADR-0009), method/prompt version, input document id, verbatim model output. Immutable — a re-run writes a new file, never overwrites. No content addressing.

   **Landmine:** add `r"^data/private/runs/$"` to `SAFE_PRIVATE_LOCATOR_PATTERNS` in `src/signalweave/public_check.py` in the *same* change that introduces the folder. Until it's added, a tracked doc that so much as names the folder trips `public-check`.

2. **Method files.** Versioned prompt(s), tracked in the repo, containing no source text — a method change becomes a reviewable diff. Location is the implementer's call (e.g. `methods/` alongside `src/`); keep it out of any `data/` zone so it's tracked by default, not ignored.

3. **Pipeline.** `segment → propose-per-segment → span-exists check → story draft → basket`. Deterministic orchestration with model steps inside it, not an agent loop — every step's input and output must be individually storable, because that's what makes a run re-runnable and, later, comparable against a different model's run on the same input.

   - `propose` extends the existing model-independent `CandidateProposer` protocol (`extract.py`, ADR-0003) with a real implementation instead of the current no-op default.
   - The only content check is mechanical (ADR-0008): the cited character span must verifiably exist in the source. Nothing else gates a record.

4. **Pass-through gate.** Every record — event, story, basket — carries `review_status: unreviewed`, `drafted_by` (model/agent identity, ADR-0007), and its run id.

5. **Export.** Same command surface as `docs/specs/thread-exposure-v0.md` DO-2 (`export-baskets --as-of ... --out ...`: thread/story id, review date, overdue flag, basket contents) but with the **one-basket** shape from this spec, not that file's three-kind shape. Nothing source-derived in the export — no summaries, no mechanism text.

   **Correction, 2026-09-13:** the line above conflated two different things — "raw source text must never leave SignalWeave" (still true, unchanged) and "the story's own synthesized mechanism/sentiment must never leave SignalWeave" (wrong: `mechanism`, `groups`, and `market_sentiment` are model-synthesized from already-abstracted candidate events, never raw transcript text, and `show-thread` already prints them with no privacy issue). The export now includes those three fields, read straight from the thread, unreworded — `open_question` and `invalidation_conditions` are still excluded, not asked for. This also resolves an inconsistency with item 6 below, which already assumed "story context as exported" would be available to render the page.

6. **The page.** Rendered by MarketPulse (it owns price and already has a render layer): story context as exported, the basket, and the basket's RS from layer 1. This is new, minimal code on the MarketPulse side that reads the export and calls `calc.py`/`baskets.py`'s existing RS math on the exported ticker list directly — it does **not** go through `narratives.py`'s hand-curated `Narrative`/`Branch` YAML schema, since narrative authoring is exactly what MarketPulse is retiring (seam decision #1).

Also folded in, no premise changed: the three friction fixes from `docs/specs/transcript-navigation-v0.md` DO-3 (`--review-id` resolution, early `--thread` validation, `--help` documenting repeatable flags).

## Acceptance

The page exists, produced unattended from one real transcript, and a reader can say what story is being told and whether the basket is strengthening or weakening. "Interesting" and "garbage" are both valid results — there is no quality bar beyond the page existing and being legible.

## Out of scope

Review gate, card lint beyond the span-exists check, two-model diff, `promptfoo`, method scorecard, `close-thread`, promotion, persona, basket membership history and the dispersion flag (M3), the post lens (M4).
