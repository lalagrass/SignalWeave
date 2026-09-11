# Roadmap

## Project state

**Current phase:** 4 — first walkthrough v0

The development, privacy, and handoff contract is complete. Candidate event
cards now have a validated schema and CLI. Private transcripts can be segmented
in memory through a model-independent dry-run boundary. Candidate reviews are
recorded as private, append-only decisions. Research threads and their updates
are implemented and awaiting verification. The loop has never been run once on
a real document: no proposer fills the inbox, and no command displays a thread.

**Last verified:** `uv sync --no-editable --reinstall-package signalweave`,
`uv run --no-sync pytest`, and
`uv run --no-sync signalweave public-check` passed on 2026-09-11.

## Completed: candidate event schema v0

The shared contract for all future lenses is implemented. Candidate cards
require traceability and uncertainty, and cannot mark themselves as accepted.

Verification passed:

```text
uv sync --no-editable
uv run --no-sync pytest
uv run --no-sync signalweave validate-event examples/event-card.example.yaml
uv run --no-sync signalweave public-check
```

## Completed: transcript extraction boundary v0

Private transcript segmentation, stable local locators, a model-independent
proposer protocol, and no-write CLI dry-run are implemented. The boundary
enforces the original segment locator and `proposed` review status for every
candidate it receives.

## Completed: inbox review v0

Reviewers can append private `keep_unlinked`, `discard`, or `link_to_thread`
records. A link is only a suggestion; it cannot mutate a thread. The CLI never
overwrites a review record.

## Implemented, pending verification: research threads v0

Human-owned threads require a mechanism, open question, invalidation conditions,
and a review date. Updates are separate dated files under
`data/private/threads/<thread_id>/updates/`. An update can only be created from a
`link_to_thread` review whose `event_id` matches, and neither a thread nor an
update can be overwritten.

Before this item is marked complete, run the documented verification commands on
a machine with a working environment and commit the working tree.

## Now: first walkthrough v0

**Status:** next implementation item. Full contract in
`docs/specs/first-walkthrough-v0.md`.

**Goal:** Make the documented success criterion executable — one real private
document turned into a visible thread update in ten minutes.

**Planned files:**

- `src/signalweave/cli.py`
- `src/signalweave/extract.py`
- `tests/test_cli.py`
- `docs/architecture.md`

**Acceptance criteria:**

- `draft-event` writes a candidate skeleton into `data/inbox/events/` carrying the
  segment's own locator and no source-derived text, and fails validation until a
  human writes `kind`, `summary`, and `uncertainty`.
- `show-thread` prints a thread's header and its dated updates with supporting and
  counter evidence under separate headings, and draws no conclusion from their
  balance.
- `list-threads --as-of <date>` marks a thread overdue from the supplied date only,
  never from the wall clock.
- `docs/architecture.md` records threads as private until a promotion step exists.
- One timed walkthrough is performed on a real document; friction notes go to
  ignored `data/private/worklog/`.
- The documented verification commands pass.

**Out of scope:** AI provider integration, research persona, reviewed-record
publishing, thread merging, update editing, and market verdicts.

## Next: reviewed event promotion v0

Introduce a de-identification step that promotes a reviewed candidate into a safe
tracked event record without copying raw source content. Deliberately sequenced
after the first walkthrough: the de-identification rules should be designed against
real cards rather than imagined ones.

## Deferred: research persona v0.1

Build only after a sufficient set of human-reviewed annotations exists. Persona
outputs are research prompts and evidence standards, never impersonated views
or trading recommendations.

## Session handoff checklist

1. State the completed roadmap item and verification results.
2. Update this file's current phase and next scoped item.
3. Record durable architectural decisions under `docs/decisions/`.
4. Keep source-specific notes in ignored `data/private/worklog/`.
