# SignalWeave

SignalWeave is a local, source-agnostic research-memory tool. It turns private
transcripts and posts into stories, each carrying a basket of instruments that
another tool can track. Market data is an independent observation; it never
decides whether a story is true, and SignalWeave never fetches a price.

## What ships first

1. Keep source material private and local.
2. Read a source into a story — groups, context, market sentiment — and a
   deliberately wide basket of possibly-implicated instruments.
3. Export the story and its basket so layer 1 can track relative strength.
4. Let the basket change over time as later sources and earnings arrive.

Records are machine-authored and the review gate is pass-through: nothing waits
for a human, and every record is stamped `review_status: unreviewed` with who
drafted it and which run produced it, so a record that was never judged is never
mistaken for one that was. See
[ADR-0008](docs/decisions/ADR-0008-machine-authored-records-and-pass-through-gate.md)
and [ADR-0009](docs/decisions/ADR-0009-model-provider-boundary.md).

The product is deliberately not a trading system, a prediction engine, or an
automatic truth classifier. No command prints a number claiming a record is good.

## Privacy and publishing

Raw material, source identities, private aliases, API keys, and generated
excerpts must never be committed. Use neutral identifiers such as `source_a`,
`doc_2026_001`, and `thread_supply_constraint` in tracked files.

Before publishing, run:

```bash
uv run signalweave public-check
```

`public-check` refuses to run until `.signalweave/private_terms.txt` exists,
because a missing file makes the term scan silently check nothing. Set it up
once per workspace:

```bash
cp .signalweave/private_terms.example.txt .signalweave/private_terms.txt
```

Then add organisation- or source-specific terms to that untracked file (one
per line; it is git-ignored and must never be committed). If a repository
genuinely has no private terms to configure, pass `--allow-unconfigured` to
run the check anyway:

```bash
uv run signalweave public-check --allow-unconfigured
```

`public-check` also flags any tracked file whose content names a path under
`data/raw/`, `data/inbox/`, or `data/private/` more specific than the bare
zone or one of its fixed subfolders (`events/`, `reviews/`, `threads/`,
`worklog/`) — a locator is itself identifying, so write about these zones in
tracked docs and tests only in the general terms above, never with a real
subpath. The command is a guardrail, not a substitute for a human review.

See [the product definition](docs/PRODUCT.md) and [privacy contract](docs/PRIVACY.md).

## Validate a candidate event

Candidate event cards are proposed observations, not accepted research records.
Validate a YAML card before placing it in the private inbox:

```bash
uv run --no-sync signalweave validate-event examples/event-card.example.yaml
```

Validation checks the required fields, controlled values, source locator, and
review gate. It does not inspect source material, create a thread, or accept a
candidate on a reviewer's behalf.

## Dry-run a transcript extraction

The first extraction boundary only segments a private file in memory and reports
counts; it never echoes source text or writes event cards. A proposer must be
configured in a later sprint before the command can create private inbox data.

```bash
uv run --no-sync signalweave extract-transcript path/to/private.md \
  --source source_a \
  --document-id doc_2026_001 \
  --date 2026-09-11 \
  --dry-run
```

## Review a candidate event

Review decisions are immutable private records. They do not modify the candidate
card or any thread. Under ADR-0008 the gate is pass-through, so this command is
for recording a judgement that a human actually made — it is not a step the
pipeline waits on:

```bash
uv run --no-sync signalweave review-event path/to/candidate.yaml \
  --action link_to_thread \
  --thread thread_supply_constraint \
  --reviewer researcher_a \
  --review-id review_2026_001
```

The record is written under ignored `data/inbox/reviews/`. Valid actions are
`keep_unlinked`, `discard`, and `link_to_thread`; only the last action accepts
`--thread`.

## Process a transcript through an interactive agent

When the current interactive coding agent has produced a private
`agent-bundle-v1` JSON file, import it locally without a project API key, SDK,
or provider request:

```bash
uv run --no-sync signalweave import-agent-bundle path/to/private.md path/to/agent-bundle-v1.json \
  --source source_a \
  --document-id doc_2026_001 \
  --date 2026-09-11
```

The bundle declares the actual provider, model, locality, and drafting identity.
Treat a cloud coding agent as `remote` unless its on-device execution is
verifiable: no project API key is not local inference. The importer segments the
private transcript locally, verifies every cited span, then writes one immutable
private bundle run and the linked unreviewed events, story, and basket. It never
constructs a provider client or makes a network request.

See [transcript processing](docs/transcript-processing.md) for the strict bundle
contract and operational boundaries.

## Process a transcript through a direct provider API

`run-pipeline` segments a transcript and runs it end to end: propose per
segment, span-exists check, story draft, basket draft. Every record it writes
is machine-authored and stamped `review_status: unreviewed` with `drafted_by`
and its run id (ADR-0008); nothing here waits for a human.

```bash
export ANTHROPIC_API_KEY=sk-...
uv run --no-sync signalweave run-pipeline path/to/private.md \
  --source source_a \
  --document-id doc_2026_001 \
  --date 2026-09-11 \
  --model-id claude-sonnet-4-5-20250929 \
  --privacy-tier remote
```

This calls the Anthropic API once per segment plus once for the story and once
for the basket, and writes one immutable run record per call under ignored
`data/private/runs/` (ADR-0009). `--privacy-tier local` refuses to run at all —
loudly, before any call — rather than silently sending a local-only source to
a remote provider. Running this against real material spends money and sends
that material to a third party. It requires separate explicit source-disclosure
and cost authorization; do not select it merely because an API key exists.

## Export baskets for MarketPulse

```bash
# Set PRIVATE_EXPORT_PATH to a private file beneath data/private/exports/.
uv run --no-sync signalweave export-baskets --as-of 2026-09-20 --out "$PRIVATE_EXPORT_PATH"
```

Emits schema v1: one entry per story with context, review date, an overdue flag,
a flat instrument basket, and separate story/basket provenance. The destination
must be a private SignalWeave export location or MarketPulse's private landing
zone. This is the seam with MarketPulse; SignalWeave never fetches a price or
ranks a basket.

## Local setup

```bash
uv sync --no-editable --reinstall-package signalweave
uv run --no-sync pytest
uv run --no-sync signalweave public-check
```

`--no-editable` keeps the command-line package importable in the current
workspace environment. `--reinstall-package signalweave` ensures the CLI uses
the current source after a code change.
