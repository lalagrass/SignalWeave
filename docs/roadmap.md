# Roadmap

## Project state

**Current phase:** 5 — milestone 2, transcript navigation v0

The development, privacy, and handoff contract is complete. Candidate event
cards have a validated schema and CLI. Private transcripts can be segmented in
memory through a model-independent dry-run boundary. Candidate reviews are
recorded as private, append-only decisions. Research threads and their updates
are implemented and verified. The loop has been closed end to end and run once
on a real private document: a candidate can be hand-drafted from a segment
locator, reviewed, linked into a thread, and the resulting thread read back
from the command line.

**Last verified:** `uv sync --no-editable --reinstall-package signalweave`,
`uv run --no-sync pytest` (56 passed), and
`uv run --no-sync signalweave public-check` (with
`.signalweave/private_terms.txt` configured locally) passed on 2026-09-12.

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
import → draft → fill → validate → review with `link_to_thread` → create
thread → append update → `show-thread`. The back-to-back command sequence
took about 35 seconds; the reviewer's own free-text judgment calls (summary,
mechanism, open question, invalidation conditions) are not part of that
measurement. Friction notes are in ignored `data/private/worklog/`; none of
them blocked completion. The ten-minute success criterion is therefore *not*
yet verified: in this run the free-text fields were written by the
implementing agent rather than by a reviewer reading the document, so what
was measured is the mechanical command sequence, not the human loop. Durable
design choices are recorded in
[ADR-0005](decisions/ADR-0005-manual-drafting-and-deterministic-readback.md).

Verification passed:

```text
uv sync --no-editable --reinstall-package signalweave
uv run --no-sync pytest        # 45 passed
uv run --no-sync signalweave public-check
```

### Follow-up fixes (planning review, 2026-09-12)

A planning review of this item found three defects, fixed before push:

1. **Privacy leak (blocking).** The `e3be52a` commit named a real private
   source path in this file. Amended into that commit rather than fixed
   forward, so the leak never existed in pushed history. `git grep` across
   the full history of both unpushed commits found no other real source
   name, path, or document date.
2. **`public-check` passed while unconfigured.** A missing
   `.signalweave/private_terms.txt` made the term scan a silent no-op, which
   is exactly how defect 1 went uncaught. `public-check` now refuses to run
   without that file (or an explicit `--allow-unconfigured`), and separately
   flags any tracked file naming a concrete path under `data/raw/`,
   `data/inbox/`, or `data/private/`. See
   [ADR-0006](decisions/ADR-0006-public-check-fails-loud-when-unconfigured.md).
3. **Misattributed authorship.** The walkthrough's thread and update recorded
   `created_by`/`added_by` as the human owner for free text the implementing
   agent actually wrote. `ResearchThread` and `ThreadUpdate` now require a
   separate `drafted_by`, shown by `show-thread` next to the owner. The one
   affected record (`thread_component_cost_passthrough`, private and
   git-ignored) was invalidated rather than migrated, since no human had
   actually reviewed its wording. See
   [ADR-0007](decisions/ADR-0007-split-drafted-by-from-created-by.md).

## Milestone 2: real material in, baskets out

Milestone 1 built the loop and proved it closes. It closed on a one-paragraph
post, with the free-text fields written by an implementing agent, and it produces
records that no other tool can read.

Milestone 2 is finished when the reviewer has run their own real material through
the loop repeatedly, without help, and the threads that result name the
instruments they implicate. Two code items, then a deliberate pause.

## Now: transcript navigation v0

**Status:** next implementation item. Contract in
`docs/specs/transcript-navigation-v0.md`.

**Goal:** Make the loop workable on a 200-line transcript rather than a
one-paragraph post.

- `list-segments` prints position, locator, and character count — never text.
- A PO decision on narrowing ADR-0003's no-echo rule for an explicit,
  human-invoked terminal print; implemented as `--show` if accepted, dropped
  entirely if not. No middle option.
- Three friction fixes from the first walkthrough: `--review-id` lookup,
  early validation of an unknown `--thread`, repeatable flags documented.

**Acceptance:** one real transcript run end to end by the reviewer — at least
three cards, one thread, two updates — with `drafted_by` recording that a human
wrote the free text. This is the first real test of the ten-minute criterion.

## Next: thread exposure v0

**Status:** specified, blocked on a PO decision. Contract in
`docs/specs/thread-exposure-v0.md`.

**Goal:** Give a thread the three baskets it implies — `if_true`, `if_false`,
`either_way` — and an export that another tool can consume. No weights, no
ordering, no scores. SignalWeave never fetches a price and never ranks a thread;
the export is the boundary.

**Decision required first:** whether SignalWeave becomes the only place stories
are authored, with MarketPulse's narrative layer retired to a consumer of
exported baskets. Two schemas for one object is the failure mode this item
exists to avoid.

## Then: usage gate — no code

Not an implementation item. After the two items above, run the loop on real
material for two weeks with no new features. The gate passes when the reviewer
can point at a thread and say either "this told me something I did not already
know" or "this is where it is wrong".

Reopen conditions for further development: a specific sentence about what was
missing. "It would be nice if" does not reopen it. If the tool is not opened
during those two weeks, that is the finding, and the next item is to ask why
rather than to build.

## Then: candidate proposer v0

**Gated on:** at least twenty human-written candidate summaries in the private
inbox.

The proposer is the point of the product and the fastest way to ruin it. With
nothing to imitate and nothing to evaluate against, its output cannot be judged,
and a review gate that rubber-stamps is worse than no gate. The twenty cards are
both the style reference and the evaluation set: a proposer is accepted only if
the reviewer keeps its cards at a rate they would defend out loud.

## Deferred: reviewed event promotion v0

Moved back from "Now". Promotion exists to make records safe to publish, and
nothing is being published: there is one local reviewer and no remote audience.
Building de-identification before there is a reason to publish means designing
rules against imagined requirements and maintaining them for nobody. Reopen when
a second person needs to read a record, or when a record must leave the machine.

## Deferred: research persona v0.1

Build only after a sufficient set of human-reviewed annotations exists. Persona
outputs are research prompts and evidence standards, never impersonated views
or trading recommendations.

## Session handoff checklist

1. State the completed roadmap item and verification results.
2. Update this file's current phase and next scoped item.
3. Record durable architectural decisions under `docs/decisions/`.
4. Keep source-specific notes in ignored `data/private/worklog/`.
