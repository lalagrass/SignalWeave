# Transcript processing

SignalWeave has two ingestion paths. Both create the same ignored private event,
story, basket, and immutable run records. Neither path treats an output as a
truth judgement: the only content check is whether each candidate's cited span
exists in the locally segmented transcript.

## Interactive-agent bundle import

Use this path when the current interactive agent has already processed a
selected private transcript. It does not use a repository API key, construct a
provider SDK client, or make a provider request. That does **not** make the
agent local inference: record a cloud agent as `remote` unless on-device model
execution is verifiable.

The bundle is strict JSON and must use this shape (all example text is
synthetic):

```json
{
  "schema_version": 1,
  "provenance": {
    "provider": "openai",
    "model_id": "gpt-synthetic-1",
    "model_locality": "remote",
    "drafted_by": "agent_synthetic",
    "method_version": "agent_bundle_v1",
    "created_at": "2026-09-13T00:00:00+00:00"
  },
  "events": [{
    "segment": 1,
    "proposals": [{
      "event_id": "evt_synthetic_001",
      "kind": "observation",
      "summary": "A synthetic observation.",
      "uncertainty": "medium",
      "cited_span": "Synthetic cited words.",
      "claims": [],
      "mechanisms": [],
      "counterarguments": [],
      "candidate_threads": ["story_synthetic_001"]
    }]
  }],
  "story": {
    "thread_id": "story_synthetic_001",
    "mechanism": "Synthetic mechanism.",
    "open_question": "Synthetic question?",
    "invalidation_conditions": ["Synthetic invalidation."],
    "groups": ["synthetic group"],
    "market_sentiment": "Synthetic sentiment.",
    "review_date": "2026-09-27"
  },
  "basket": {"instruments": ["2330", "2454"]}
}
```

`source`, `source_locator`, event date, review status, and run id are importer
owned. The bundle must not supply them. The command rejects unsupported fields,
missing/invalid provenance, unavailable segments, missing spans, duplicate
event ids, and any destination collision before writing anything.

```bash
uv run --no-sync signalweave import-agent-bundle path/to/private.md path/to/agent-bundle-v1.json \
  --source source_a --document-id doc_2026_001 --date 2026-09-11
```

Keep the transcript and bundle in ignored local storage. The importer writes one
`agent_bundle_v1` run with the canonical bundle as its private output, and all
records point to that shared run. Do not re-import an already recorded bundle;
collisions are an intentional refusal.

## Direct provider API

`run-pipeline` sends transcript material to a provider. Before invoking it on a
real source, obtain explicit authorization for that disclosure and the expected
cost, choose the provider/model, and record the source's privacy tier. An API
key's presence is not authorization and must not select this path by default.

See [ADR-0009](decisions/ADR-0009-model-provider-boundary.md) and
[ADR-0011](decisions/ADR-0011-interactive-agent-transcript-processing.md).
