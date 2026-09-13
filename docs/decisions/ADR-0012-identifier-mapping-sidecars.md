# ADR-0012: Canonical identity uses immutable mapping sidecars

## Status

Accepted.

## Context

SignalWeave baskets deliberately preserve a wide, machine-drafted set of
declared identifiers. MarketPulse cannot safely turn those names into price
symbols by guessing. At the same time, correcting a canonical identity must
not rewrite the basket snapshot that an earlier run produced.

`agent-bundle-v1` also predates canonical mapping output. Extending it in
place would make an old version label dishonest.

## Decision

Keep baskets and `agent-bundle-v1` immutable. Add private,
append-only `identifier-mapping-v1` records, each bound to the exact
`thread_id`, basket `run_id`, and basket `created_at`. A mapping covers every
declared member exactly once and in the same order. It can state only:

- `resolved` with canonical venue and symbol;
- `unresolved` with null identity fields and a reason; or
- `not_publicly_listed` with null identity fields.

Each mapping has its own run and complete provenance. Corrections create a new
`mapping_id` that explicitly supersedes the active mapping; ambiguous active
mappings are export errors. Export v2 includes the mapped members and mapping
provenance. It does not change v1 documents.

The supported import path accepts a strict ignored-private mapping bundle and
derives the basket snapshot fields and mapping run id locally. It validates the
whole operation before writing the immutable run and sidecar together; operators
do not construct either stored record by hand.

MarketPulse decides whether a resolved venue is supported and whether a symbol
has as-of price data. It must consume only explicit supported symbols, never
infer aliases or treat unresolved identity as a negative market signal.

If an interactive agent later natively produces mappings in one payload, add
`agent-bundle-v2`; do not retrofit fields into v1.

## Consequences

- Existing baskets/runs remain reproducible and unmodified.
- Export requires a complete, unambiguous private mapping for each basket
  snapshot; there is no fallback name resolver.
- Identity mapping is provenance-distinct from both story and basket drafting.
- MarketPulse can honestly separate unsupported venue, unresolved identity,
  non-public listing, and missing as-of price without changing its RS formula.
