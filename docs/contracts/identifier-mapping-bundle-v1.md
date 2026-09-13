# Identifier mapping bundle v1

An interactive agent writes this strict JSON bundle into an ignored private
directory after reading one already-written basket. The supported importer owns
the basket snapshot fields and mapping run id; an operator never writes either
record by hand.

```json
{
  "schema_version": 1,
  "mapping_id": "mapping_synthetic001",
  "supersedes_mapping_id": null,
  "provenance": {
    "provider": "openai",
    "model_id": "gpt-synthetic-1",
    "model_locality": "remote",
    "drafted_by": "mapping_agent_synthetic",
    "method_version": "identifier_mapping_v1",
    "created_at": "2026-09-13T00:00:00+00:00"
  },
  "members": [
    {
      "declared_identifier": "synthetic_one",
      "mapping_status": "resolved",
      "venue": "TWSE",
      "symbol": "1234",
      "reason": null
    },
    {
      "declared_identifier": "synthetic_two",
      "mapping_status": "unresolved",
      "venue": null,
      "symbol": null,
      "reason": "No canonical listing supplied."
    }
  ]
}
```

All root, provenance, and member fields are exact; unknown or missing fields are
errors. Members must repeat the bound basket one for one and in the same order.
The only method version accepted by this contract is
`identifier_mapping_v1`. A correction names the currently active mapping in
`supersedes_mapping_id`; a first revision uses null.

Import from the verified SignalWeave repository root:

```bash
# Set PRIVATE_MAPPING_BUNDLE to the ignored JSON bundle path.
uv run --no-sync signalweave import-identifier-mapping \
  "$PRIVATE_MAPPING_BUNDLE" \
  --thread story_synthetic_001
```

The command validates the complete operation before writing. On success it
creates one immutable run under the private runs directory and one immutable
sidecar under the private identifier-mappings directory. A failed write rolls
back both new paths; if the filesystem also refuses cleanup, the command reports
an incomplete rollback explicitly rather than claiming that no record remains.
CLI output contains only a safe outcome count or recovery instruction, never
member values or private paths.
