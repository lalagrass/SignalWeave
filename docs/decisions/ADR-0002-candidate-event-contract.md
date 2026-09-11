# ADR-0002: Require strict, review-gated candidate event cards

## Status

Accepted

## Context

Transcript, post, and future persona lenses need a common output contract.
Without one, their observations cannot be consistently reviewed, linked, or
audited. The contract must preserve uncertainty and source traceability without
allowing an extractor to promote its own output into research truth.

## Decision

Define `CandidateEvent` as a strict YAML-backed record. It requires a stable
event id, neutral source id, source locator, ISO date, event kind, concise
summary, review status, and uncertainty. Candidate records may include claims,
mechanisms, counterarguments, and suggested thread links.

The only allowed candidate review statuses are `proposed`, `keep_unlinked`, and
`discarded`. `accepted` is deliberately invalid at this layer; acceptance is a
separate human-review action that will create a reviewed record.

## Consequences

- All future lenses produce the same reviewable shape.
- Source traceability and uncertainty are mandatory rather than optional.
- The validation CLI can reject malformed private inbox cards before review.
- A future reviewed-event schema must model acceptance explicitly instead of
  mutating a candidate into an untraceable final record.
