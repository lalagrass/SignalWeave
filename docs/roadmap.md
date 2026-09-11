# Roadmap

## Project state

**Current phase:** 2 — inbox review v0

The development, privacy, and handoff contract is complete. Candidate event
cards now have a validated schema and CLI. Private transcripts can be segmented
in memory through a model-independent dry-run boundary. No review workflow or
reviewed research records have been implemented yet.

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

## Now: inbox review v0

**Status:** next implementation item

**Goal:** Let a reviewer explicitly keep, discard, or link a validated private
candidate event without mutating source content or a thread directly.

**Planned files:**

- `src/signalweave/extract.py`
- `src/signalweave/review.py`
- `src/signalweave/cli.py`
- `tests/test_extract.py`
- `tests/test_review.py`

**Acceptance criteria:**

- Only explicit reviewer actions may change a candidate's review state.
- Linking records a suggested thread identifier but does not merge or mutate a
  thread.
- Review output remains private until a separate de-identification step exists.
- Tests use only synthetic source material.
- The documented verification commands pass.

**Out of scope:** AI provider integration, reviewed-record publishing, thread
merging, and persona extraction.

## Next: inbox review v0

Accept, reject, keep unlinked, or suggest a link to an existing thread. Review
must be explicit and append-only.

## Later: threads v0

Add reviewed events as dated supporting or counter evidence, with open
questions, invalidation conditions, and review dates.

## Deferred: research persona v0.1

Build only after a sufficient set of human-reviewed annotations exists. Persona
outputs are research prompts and evidence standards, never impersonated views
or trading recommendations.

## Session handoff checklist

1. State the completed roadmap item and verification results.
2. Update this file's current phase and next scoped item.
3. Record durable architectural decisions under `docs/decisions/`.
4. Keep source-specific notes in ignored `data/private/worklog/`.
