# SignalWeave development contract

## Product boundary

SignalWeave turns private-source material into stories that each carry a basket
of instruments. It is not a trading system, a price-prediction engine, or an
automatic truth classifier. It never fetches a price, never ranks a story, and
never scores a basket.

## Privacy boundary

- Never read, quote, copy, or commit raw source content into tracked files.
- Raw inputs belong in `data/raw/`; generated work belongs in `data/inbox/` and
  `data/private/`; all are Git-ignored.
- Use neutral source identifiers and locators in tracked examples and tests.
- Raw source text may be sent to a model provider under the rules in
  [ADR-0009](docs/decisions/ADR-0009-model-provider-boundary.md). Every run
  records which provider and locality it used.
- Before a handoff or release, run
  `uv sync --no-editable --reinstall-package signalweave`, then
  `uv run --no-sync pytest` and `uv run --no-sync signalweave public-check`.

## Research boundary

- An event is a neutral, dated observation. A story is a hypothesis about a
  mechanism. A basket is the set of instruments a story implicates.
- Records are machine-authored. The review gate is pass-through: nothing waits
  for a human, and every record is stamped `review_status: unreviewed` with its
  `drafted_by` and its run id. A record that was never judged must never be
  indistinguishable from one that was. See
  [ADR-0008](docs/decisions/ADR-0008-machine-authored-records-and-pass-through-gate.md).
- Every event must retain a `source_locator` and the character span it cites;
  summaries must not be copied quotations. The span must verifiably exist in the
  source — that is the only content check the pipeline performs.
- A basket starts wide on purpose and changes over time. Membership changes are
  dated, carry a reason, and are append-only.
- Keep supporting and counter evidence distinct. Story updates are append-only.

## Development workflow

The authoritative checkout is the Git repository whose configured remote is
SignalWeave. Before editing, resolve its root with Git and verify that remote; do
not work from copied output folders or transplant `.git` metadata between
directories.

1. Read `docs/architecture.md`, `docs/roadmap.md`, and relevant ADRs.
2. Choose one roadmap item with explicit acceptance criteria.
3. Add or update tests before declaring the item complete.
4. Keep changes scoped; record durable design choices as an ADR.
5. Update the roadmap with verification results and the next handoff item.

A milestone's acceptance is something a reader can look at, not a list of
commands that exit zero. Tests still have to pass; they are not the deliverable.

When the user asks to plan, start, continue, or run a sprint, use the repository
skill `signalweave-sprint`. It authorizes read-only delegation to the project PO,
correctness reviewer, and privacy reviewer while keeping the main agent as the
only file writer. See `docs/development-workflow.md`.

## Handoff protocol

Tracked handoffs may describe code, schemas, tests, and non-sensitive status.
Put source-specific annotations, locators with identifying details, and private
research notes only in `data/private/worklog/`.
