# SignalWeave development contract

## Product boundary

SignalWeave helps a reviewer turn private-source material into auditable
research threads. It is not a trading system, a price-prediction engine, or an
automatic truth classifier.

## Privacy boundary

- Never read, quote, copy, or commit raw source content into tracked files.
- Raw inputs belong in `data/raw/`; candidate work belongs in `data/inbox/`;
  both are Git-ignored.
- Use neutral source identifiers and locators in tracked examples and tests.
- Before a handoff or release, run `uv sync --no-editable`, then
  `uv run --no-sync pytest` and `uv run --no-sync signalweave public-check`.

## Research boundary

- An event is a neutral, dated observation. A thread is a human-owned causal
  hypothesis.
- AI may propose candidate cards, links, questions, and counterarguments. A
  reviewer alone accepts a card, creates or merges a thread, or declares an
  outcome.
- Every accepted event must retain a `source_locator`; summaries must not be
  copied quotations.
- Keep supporting and counter evidence distinct. Thread updates are
  append-only.

## Development workflow

1. Read `docs/architecture.md`, `docs/roadmap.md`, and relevant ADRs.
2. Choose one roadmap item with explicit acceptance criteria.
3. Add or update tests before declaring the item complete.
4. Keep changes scoped; record durable design choices as an ADR.
5. Update the roadmap with verification results and the next handoff item.

## Handoff protocol

Tracked handoffs may describe code, schemas, tests, and non-sensitive status.
Put source-specific annotations, locators with identifying details, and private
research notes only in `data/private/worklog/`.
