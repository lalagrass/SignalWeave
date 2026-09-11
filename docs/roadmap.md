# Roadmap

## Project state

**Current phase:** 3 — research threads v0

The development, privacy, and handoff contract is complete. Candidate event
cards now have a validated schema and CLI. Private transcripts can be segmented
in memory through a model-independent dry-run boundary. Candidate reviews are
now recorded as private, append-only decisions. No research threads or reviewed
research records have been implemented yet.

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

## Now: research threads v0

**Status:** next implementation item

**Goal:** Create human-owned, append-only hypothesis threads that can receive
reviewed supporting and counter evidence.

**Planned files:**

- `src/signalweave/threads.py`
- `src/signalweave/cli.py`
- `tests/test_threads.py`

**Acceptance criteria:**

- A thread requires a human-written mechanism, open question, invalidation
  condition, and review date.
- Updates append dated supporting or counter evidence without altering older
  entries.
- A thread update can cite an event and review record, but never copies raw
  source text.
- Tests use only synthetic source material.
- The documented verification commands pass.

**Out of scope:** AI provider integration, reviewed-record publishing, thread
merging, market verdicts, and persona extraction.

## Next: reviewed event promotion v0

Introduce a de-identification step that promotes a reviewed candidate into a
safe tracked event record without copying raw source content.

## Deferred: research persona v0.1

Build only after a sufficient set of human-reviewed annotations exists. Persona
outputs are research prompts and evidence standards, never impersonated views
or trading recommendations.

## Session handoff checklist

1. State the completed roadmap item and verification results.
2. Update this file's current phase and next scoped item.
3. Record durable architectural decisions under `docs/decisions/`.
4. Keep source-specific notes in ignored `data/private/worklog/`.
