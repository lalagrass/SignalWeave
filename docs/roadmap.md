# Roadmap

## Project state

**Current phase:** 5 — reviewed event promotion v0

The development, privacy, and handoff contract is complete. Candidate event
cards have a validated schema and CLI. Private transcripts can be segmented in
memory through a model-independent dry-run boundary. Candidate reviews are
recorded as private, append-only decisions. Research threads and their updates
are implemented and verified. The loop has been closed end to end and run once
on a real private document: a candidate can be hand-drafted from a segment
locator, reviewed, linked into a thread, and the resulting thread read back
from the command line.

**Last verified:** `uv sync --no-editable --reinstall-package signalweave`,
`uv run --no-sync pytest` (45 passed), and
`uv run --no-sync signalweave public-check` passed on 2026-09-12.

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

## Completed: research threads v0

Human-owned threads require a mechanism, open question, invalidation conditions,
and a review date. Updates are separate dated files under
`data/private/threads/<thread_id>/updates/`. An update can only be created from a
`link_to_thread` review whose `event_id` matches, and neither a thread nor an
update can be overwritten. Verified and committed on 2026-09-12.

## Completed: first walkthrough v0

`draft-event` writes a candidate skeleton into `data/inbox/events/` carrying the
segment's own locator and no source-derived text; it fails validation until a
human writes `kind`, `summary`, and `uncertainty`. `show-thread` prints a
thread's header and its dated updates with supporting and counter evidence
under separate headings, drawing no conclusion from their balance.
`list-threads --as-of <date>` marks a thread overdue from the supplied date
only, computed without ever calling the wall clock. `docs/architecture.md` now
records threads as private (`data/private/threads/`) until a promotion step
exists.

One timed walkthrough was run on one real private document, held locally
under an ignored path and referred to here only as `source_a`/`doc_2026_101`:
import → draft → fill → validate → review
with `link_to_thread` → create thread → append update → `show-thread`. The
back-to-back command sequence took about 35 seconds; the reviewer's own
free-text judgment calls (summary, mechanism, open question, invalidation
conditions) are not part of that measurement. Friction notes are in ignored
`data/private/worklog/2026-09-12-first-walkthrough.md`; none of them blocked
completion. The ten-minute success criterion is therefore *not* yet
verified: in this run the free-text fields were written by the implementing
agent rather than by a reviewer reading the document, so what was measured is
the mechanical command sequence, not the human loop. Durable
design choices are recorded in
[ADR-0005](decisions/ADR-0005-manual-drafting-and-deterministic-readback.md).

Verification passed:

```text
uv sync --no-editable --reinstall-package signalweave
uv run --no-sync pytest        # 45 passed
uv run --no-sync signalweave public-check
```

## Now: reviewed event promotion v0

**Status:** next implementation item.

**Goal:** Introduce a de-identification step that promotes a reviewed candidate
into a safe tracked event record without copying raw source content.
Deliberately sequenced after the first walkthrough: the de-identification
rules should be designed against the real candidate and review records that
now exist in `data/inbox/` rather than imagined ones.

**Out of scope:** AI provider integration, research persona, thread promotion
or merging, market verdicts.

## Deferred: research persona v0.1

Build only after a sufficient set of human-reviewed annotations exists. Persona
outputs are research prompts and evidence standards, never impersonated views
or trading recommendations.

## Session handoff checklist

1. State the completed roadmap item and verification results.
2. Update this file's current phase and next scoped item.
3. Record durable architectural decisions under `docs/decisions/`.
4. Keep source-specific notes in ignored `data/private/worklog/`.
