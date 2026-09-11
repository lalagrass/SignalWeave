# Spec: first walkthrough v0

**Roadmap item:** first walkthrough v0
**Precondition:** the research-threads v0 working tree is verified and committed.
**Appetite:** one session. Two new CLI commands, one documentation correction.

## Why this before reviewed-event promotion

The loop is open at both ends. `extract-transcript` runs the `NoopCandidateProposer`,
so it emits zero candidates: the only way to obtain a card is to hand-write YAML and
hand-copy a segment locator. At the other end, once an update is appended, nothing can
display it. Reviewed-event promotion designs a de-identification rule for records that
do not yet exist; it should be designed after real cards exist, not before.

This item makes the documented success criterion executable: *after importing one new
private document, a reviewer can turn its useful ideas into traceable thread updates
within ten minutes.*

## DO-1 — `draft-event`

Write a pre-filled candidate card skeleton into the private inbox.

```bash
uv run --no-sync signalweave draft-event path/to/private.md \
  --source source_a \
  --document-id doc_2026_001 \
  --date 2026-09-11 \
  --segment 12 \
  --event-id evt_2026_001
```

Behaviour:

- Segment the private file with the existing `segment_transcript` boundary and select
  the segment at the requested position. An out-of-range position is an error naming
  the available range, and must not echo any source text.
- Write `data/inbox/events/<event_id>.yaml` containing the machine-known fields only:
  `event_id`, `source`, `source_locator` (the segment's own locator, taken from the
  segmentation boundary, never constructed by hand), `date`, and
  `review_status: proposed`.
- Emit the human-owned fields `kind`, `summary`, and `uncertainty` as empty values, and
  the optional list fields as empty lists.
- Refuse to overwrite an existing file, consistent with `write_review`.

**The draft is deliberately invalid until a human fills it in.** Running
`validate-event` on a fresh draft must fail with an error naming the missing human
field. A test must assert exactly that: draft → validate fails → fill `kind`,
`summary`, `uncertainty` → validate passes.

Privacy constraints, non-negotiable:

- The draft file must not contain segment text, an excerpt, a first sentence, or a
  generated summary. It carries the locator and nothing source-derived.
- The command must not print source text to stdout. Do not add a "show me the segment"
  convenience; the reviewer reads their own file in their own editor.

## DO-2 — read side

Two commands over the private thread store.

```bash
uv run --no-sync signalweave show-thread thread_supply_constraint
uv run --no-sync signalweave list-threads --as-of 2026-09-11
```

`show-thread`:

- Print the thread header (mechanism, open question, invalidation conditions, review
  date) followed by its updates ordered by `date`, then `update_id` for ties.
- Print supporting and counter evidence under separate headings. Do not merge, score,
  count against each other, or draw a conclusion from the balance of the two.
- Each update line shows its date, summary, and cited `event_id` / `review_id`.

`list-threads`:

- One line per thread: id, review date, update count, and an `OVERDUE` marker when
  `review_date < --as-of`.
- `--as-of` is required and is the only source of "today". Do not call
  `date.today()`; staleness must be computed from the supplied date so the output is
  deterministic and testable.

Both commands read `data/private/threads/`, the directory `write_thread` already uses.

## DO-3 — correct the architecture diagram

`docs/architecture.md` shows threads landing in `data/reviewed/threads/`, but
`create-thread` writes to `data/private/threads/`. The code is right: a thread is
private until a promotion step exists to de-identify it. Correct the diagram and the
storage-zone table to match, and note that a tracked `data/reviewed/threads/` is
introduced by the later promotion item.

## Acceptance

1. `uv sync --no-editable --reinstall-package signalweave`,
   `uv run --no-sync pytest`, and `uv run --no-sync signalweave public-check` pass.
2. Tests use synthetic source material only.
3. The timed walkthrough is performed once on one real private document: import,
   draft, fill, validate, review with `link_to_thread`, create thread, append update,
   `show-thread`. Record the elapsed time and every point of friction.
4. The friction list goes to ignored `data/private/worklog/`. Only the non-sensitive
   outcome — elapsed time and the names of the rough steps — goes in the roadmap.

The walkthrough is part of the acceptance, not a follow-up. An item that ships two
commands without one real run has not been verified.

## Out of scope

AI or LLM proposer, research persona, reviewed-event promotion and de-identification,
thread merging, editing or deleting an existing update, market data, any output that
ranks or scores threads against each other.

## Handoff prompt

> Implement the roadmap item "first walkthrough v0" in this repository. Read AGENTS.md,
> docs/architecture.md, docs/roadmap.md, docs/decisions/, and
> docs/specs/first-walkthrough-v0.md first; the spec is the contract and its privacy
> constraints are not negotiable. Before starting, verify and commit the existing
> research-threads working tree if it is still uncommitted. Add or update tests before
> declaring any DO complete, keep the change scoped to the three DOs, record any durable
> design choice as a new ADR, and update docs/roadmap.md with the verification results
> and the next item. Do not merge to any branch. Report what you did, what the
> verification commands printed, and anything in the spec that turned out to be wrong.
