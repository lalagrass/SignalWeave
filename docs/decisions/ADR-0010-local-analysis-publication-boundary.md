# ADR-0010: Privacy protects publication, not local analysis

## Status

Accepted.

## Context

SignalWeave exists to analyze source material locally and turn it into research
records. An earlier instruction said to "never read" raw source content while
also saying the real promise was that source material never enters a public
repository. An agent followed the broader wording and refused to hash or compare
local files, leaving a content-equivalence check for the user.

That behavior does not match the product intent. The protected boundary is Git
and publication. Local analysis is necessary for extraction, provenance checks,
deduplication, and research.

## Decision

- Agents and local tools may open, read, parse, hash, compare, and transform
  source material inside the authorized workspace.
- Content-based provenance, identity, and equivalence checks are allowed. An
  agent should perform them when useful instead of asking the user to attest to
  a fact solely because the inputs are private.
- Raw inputs and source-specific intermediate work remain in Git-ignored private
  zones. They must not be staged, committed, or copied into public artifacts.
- Tracked records use neutral identifiers and de-identified summaries. Raw or
  distinctive passages should not be reproduced in terminal output, reviews, or
  handoffs when a targeted inspection, count, or hash is sufficient.
- Sending source text to a model remains governed by ADR-0009; this decision does
  not widen provider access.

## Consequences

- Agents can validate whether two local files represent the same source and can
  inspect source material to perform the product's actual research work.
- Privacy review focuses on repository and publication leakage rather than
  treating local read access as a violation.
- `public-check`, ignored private zones, staged-diff review, and human publication
  review remain the release controls.
