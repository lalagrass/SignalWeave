# SignalWeave export v1

MarketPulse accepts only `schema_version: 1` (an integer). An absent, wrong, or
unsupported version fails before page rendering; re-export from SignalWeave
rather than inventing a compatibility path.

```yaml
schema_version: 1
as_of: "2026-09-20"
generated_at: "2026-09-20T00:00:00+00:00"
stories:
  - thread_id: "story_synthetic_001"
    review_date: "2026-10-04"
    overdue: false
    mechanism: "Synthetic mechanism."
    groups: ["synthetic group"]
    market_sentiment: "Synthetic sentiment."
    provenance:
      review_status: "unreviewed"
      drafted_by: "model_synthetic"
      run_id: "run_story_synthetic001"
      method_version: "story_v1"
    basket:
      instruments: ["2330", "2454"]
      provenance:
        review_status: "unreviewed"
        drafted_by: "model_synthetic"
        run_id: "run_basket_synthetic001"
        method_version: "basket_v1"
```

`overdue` must equal `review_date < as_of`. Story and basket provenance are
separate because their runs may differ. `method_version` is resolved from the
immutable run named by `run_id`, never guessed by the exporter. The canonical
synthetic fixture is `tests/fixtures/signalweave-export-v1.yaml`; MarketPulse
vendors an identical test fixture for independent-clone verification.

The exporter refuses public destinations. It may write only below
`data/private/exports/` in SignalWeave or the sibling
`MarketPulse/data/private/signalweave/` landing zone, both ignored roots.
