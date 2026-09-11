# ADR-0007: Track who drafted a thread's text separately from who owns it

## Status

Accepted

## Context

`create_thread` and `create_thread_update` recorded a single identity
(`created_by`, `added_by`) for a thread and its updates. The first
walkthrough ran end to end with the implementing agent invoking these
commands directly, writing the mechanism, open question, invalidation
conditions, and update summaries itself, while `created_by`/`added_by` were
set to the human owner's id. The resulting record read as if a human had
composed that free text and accepted it, when neither had happened: no human
had reviewed the specific wording before it was written to
`data/private/threads/`.

SignalWeave's premise is that a thread is a human-owned hypothesis (AGENTS.md
"Research boundary"; `docs/PRODUCT.md`). A schema that cannot distinguish
"a human wrote and accepts this" from "something else wrote it and a human's
id got attached anyway" cannot enforce that premise — it can only assume it.

## Decision

Add a required `drafted_by` field to both `ResearchThread` and `ThreadUpdate`,
alongside the existing `created_by` / `added_by`. `created_by`/`added_by` is
the human who accepts and owns the record. `drafted_by` is whoever produced
its free text — a human id, or an agent identifier when a human has not
composed that text themselves. The two may hold the same id when a human
genuinely wrote their own record, but the field is always required so an
agent-drafted record cannot default to looking human-authored by omission.
`create-thread` and `append-thread-update` both require `--drafted-by`;
`show-thread` prints it next to the owner on the thread header and on every
update line.

The one existing record produced before this field existed
(`thread_component_cost_passthrough`, written during the first walkthrough)
is invalidated rather than migrated: it is private, git-ignored demo data
with no real human review behind its `created_by`/`added_by` attribution, so
backfilling `drafted_by` to make it schema-valid again would still leave a
misattributed owner on record. It has been deleted rather than patched.

## Consequences

- A thread or update cannot pass validation without stating whether a human
  or an agent produced its wording, closing the gap that let the first
  walkthrough's demo record misattribute agent-written text to a human
  owner.
- `created_by`/`added_by` remains the single field that matters for
  accountability and ownership; `drafted_by` is provenance, not an
  additional approval gate — nothing currently reads it to change behavior.
- Existing private thread/update files written before this change are
  missing `drafted_by` and will fail to load until a human re-creates them
  (or a future migration adds the field); none currently exist in this
  workspace.
- A future reviewed-event or thread-promotion step can use `drafted_by` to
  decide whether agent-drafted text still needs a human rewrite before
  publication, without having to guess from `created_by` alone.
