# ADR-0004: Store reviewer decisions as append-only private records

## Status

Accepted

## Context

Candidate cards represent proposed observations. The reviewer must be able to
record a decision without overwriting source-derived data or making an implicit
change to a research thread. Reviews may contain sensitive rationale and must
not be published with the application.

## Decision

Represent every decision as a separate `ReviewRecord` stored under ignored
`data/inbox/reviews/`. Supported actions are `keep_unlinked`, `discard`, and
`link_to_thread`. Linking stores only a suggested thread identifier; it does
not create, merge, or update a thread. The CLI requires an explicit review ID
and refuses to overwrite an existing record.

## Consequences

- Review history is preserved rather than hidden by candidate mutation.
- The reviewer retains control over promotion into research threads.
- Private rationale remains outside version control.
- A future thread workflow must read review records explicitly rather than
  treating a candidate status as final truth.
