# Roadmap

## Project state

**Current phase:** 1 — transcript extraction v0

The development, privacy, and handoff contract is complete. Candidate event
cards now have a validated schema and CLI. No extractor, review workflow, or
reviewed research records have been implemented yet.

**Last verified:** `uv sync --no-editable`, `uv run --no-sync pytest`, and
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

## Now: transcript extraction v0

**Status:** next implementation item

**Goal:** Turn one transcript into private, human-reviewable candidate event
cards without inspecting or publishing source text outside the private data
zone.

**Planned files:**

- `src/signalweave/extract.py`
- `src/signalweave/cli.py`
- `tests/test_extract.py`

**Acceptance criteria:**

- Synthetic transcript segments can be supplied through a private input
  interface without exposing their text in tracked output.
- The extractor returns only `proposed` candidate events and always includes a
  locator and uncertainty.
- The extractor may return no candidates when no segment meets its threshold.
- Tests use only synthetic source material.
- The documented verification commands pass.

**Out of scope:** AI provider integration, automatic review, thread merging,
and persona extraction.

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
