# ADR-0005: Manual candidate drafting and deterministic, read-only thread display

## Status

Accepted

## Context

Two loop-closing gaps blocked the documented success criterion. First,
`extract-transcript` only runs the `NoopCandidateProposer`, so the inbox stays
empty until an AI provider exists; the only way to get a candidate card was to
hand-write YAML and hand-copy a segment locator, which is error-prone and
invites a reviewer to paste source wording by hand. Second, once a thread
update existed there was no command to read it back; a thread's state was
only visible by opening its private YAML files directly.

## Decision

Add `draft-event`, which reuses the existing `segment_transcript` boundary to
select one segment and write a schema-shaped skeleton into
`data/inbox/events/`. The skeleton carries only machine-known fields
(`event_id`, `source`, `source_locator`, `date`, `review_status: proposed`)
and emits `kind`, `summary`, and `uncertainty` empty, so `validate-event`
deliberately fails until a human fills them in. The command never prints
segment text and refuses to overwrite an existing draft.

Add `show-thread` and `list-threads` as pure, read-only commands over
`data/private/threads/`. Neither command mutates state. `show-thread` lists
supporting and counter updates under separate headings without scoring or
netting them against each other. `list-threads` takes a required `--as-of`
date and computes overdue status only from that value, never from
`date.today()`, so its output is deterministic and testable.

## Consequences

- A reviewer can populate the inbox without an AI proposer and without
  hand-copying a locator, while the schema still enforces that acceptance
  criteria (kind, summary, uncertainty) are a human decision, not a default.
- Command output can never leak source text: `draft-event` writes only
  locator and status fields, and errors (e.g. an out-of-range segment
  position) name counts, never content.
- Thread visibility has no wall-clock dependency; `list-threads --as-of`
  produces the same output for the same inputs regardless of when it runs,
  which keeps it testable and keeps "overdue" a caller-supplied judgment
  rather than an implicit one.
- A future AI proposer can replace manual drafting without changing the
  inbox schema or the review gate, since `draft-event` produces the same
  shape `extract_candidates` already enforces.
