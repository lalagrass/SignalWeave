# ADR-0001: Separate private inputs from reviewable research records

## Status

Accepted

## Context

SignalWeave works with transcripts and posts that may contain copyrighted,
identifying, or otherwise private material. The project needs durable research
records without making the original material publishable by accident.

## Decision

Store original material, candidate cards, identity maps, and private worklogs
under Git-ignored `data/raw/`, `data/inbox/`, and `data/private/`. Store only
human-reviewed and de-identified events and thread records in `data/reviewed/`.
Every event retains a local source locator, but tracked records use neutral
source identifiers.

## Consequences

- Public examples and tests use synthetic sources only.
- The repository can contain product logic and approved research artefacts
  without containing raw source text.
- Review is an explicit boundary rather than an informal convention.
