# Roadmap

## Project state

**Current phase:** 1 — transcript extraction v0

The development, privacy, and handoff contract is complete. The repository has
publication guardrails and a private source layout. No extractor, review
workflow, or research records have been implemented yet.

**Last verified:** `uv sync --no-editable`, `uv run --no-sync pytest`, and
`uv run --no-sync signalweave public-check` passed on 2026-09-11.

## Now: transcript extraction v0

**Status:** next implementation item

**Goal:** Turn one transcript into private, human-reviewable candidate event
cards without inspecting or publishing source text outside the private data
zone.

**Planned files:**

- `src/signalweave/schema.py`
- `src/signalweave/extract.py`
- `src/signalweave/cli.py`
- `tests/test_schema.py`
- `tests/test_extract.py`

**Acceptance criteria:**

- A candidate event requires `event_id`, `source`, `source_locator`, `date`,
  `kind`, `summary`, `review_status`, and `uncertainty`.
- Invalid records fail with actionable validation errors.
- Candidate output always includes a locator and never marks itself accepted.
- Tests use only synthetic source material.
- `uv run pytest` and `uv run signalweave public-check` pass.

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
