# SignalWeave export v2

MarketPulse accepts only integer `schema_version: 2` for the v2 story-page
path. A v1 export remains an immutable v1 document; it is not reinterpreted or
silently upgraded. Re-export after creating an identity mapping instead.

```yaml
schema_version: 2
as_of: "2026-09-20"
generated_at: "2026-09-20T00:00:00+00:00"
stories:
  - thread_id: "story_synthetic_001"
    review_date: "2026-10-04"
    overdue: false
    mechanism: "Synthetic mechanism."
    groups: ["synthetic group"]
    market_sentiment: "Synthetic sentiment."
    provenance: {review_status: "unreviewed", drafted_by: "model_synthetic", run_id: "run_story_synthetic001", method_version: "story_v1"}
    basket:
      members:
        - declared_identifier: "synthetic_twse"
          mapping_status: "resolved"
          venue: "TWSE"
          symbol: "2330"
          reason: null
        - declared_identifier: "synthetic_unknown"
          mapping_status: "unresolved"
          venue: null
          symbol: null
          reason: "No canonical listing supplied."
      provenance: {review_status: "unreviewed", drafted_by: "model_synthetic", run_id: "run_basket_synthetic001", method_version: "basket_v1"}
      identifier_provenance:
        review_status: "unreviewed"
        drafted_by: "mapping_agent_synthetic"
        run_id: "run_mapping_synthetic001"
        provider: "synthetic_provider"
        model_id: "synthetic-mapper"
        model_locality: "local"
        method_version: "identifier_mapping_v1"
        created_at: "2026-09-20T00:00:00+00:00"
```

## Identity contract

`basket.members` is a one-for-one, same-order projection of the immutable
SignalWeave basket. Every member has the exact fields shown above and retains
its original `declared_identifier`; mapping must not add, remove, repeat, or
reorder basket members.

- `resolved` requires canonical `venue` and `symbol`; `reason` is null.
- `unresolved` has null `venue`/`symbol` and a non-empty `reason`.
- `not_publicly_listed` has null `venue`/`symbol`; `reason` is null or a
  non-empty explanation.

The mapping status is an identity statement only. `unsupported_venue` is
MarketPulse's decision from its current supported-venue set, and
`no_as_of_price` is its point-in-time price-data result. Neither is a
SignalWeave mapping status or a negative signal about the story.

## Private mapping input

SignalWeave constructs v2 from a private `identifier-mapping-v1` sidecar in
`data/private/identifier-mappings/`. Each immutable mapping includes
`thread_id`, `basket_run_id`, and `basket_created_at`, and has independent
mapping provenance. The provenance must match its recorded mapping run. A
correction creates a new `mapping_id` with `supersedes_mapping_id`; an export
refuses missing or multiple active mappings for the exact basket snapshot.
Existing baskets and v1 exports are never modified.

The canonical synthetic fixture is
`tests/fixtures/signalweave-export-v2.yaml`; MarketPulse vendors a byte-identical
copy for independent-clone verification. Exports may write only below
SignalWeave's `data/private/exports/` or MarketPulse's ignored
`data/private/signalweave/` landing zone.
