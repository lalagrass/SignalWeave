# ADR-0011: Import interactive-agent transcript bundles locally

## Status

Accepted.

## Context

SignalWeave already supports a direct provider API pipeline. That is not the
only way private material can be processed: the current interactive coding
agent may inspect a selected private transcript and produce structured output.
The absence of a repository-managed API key does not make that processing local
inference, and it must not erase the actual provider/model/locality provenance.

The repository still needs deterministic validation before an agent result
becomes a SignalWeave record. In particular, every candidate's cited span must
be checked against the locally segmented transcript, and invalid input must not
create a partial set of records.

## Decision

Add a strict JSON `agent-bundle-v1` contract and a no-network
`import-agent-bundle` command. A valid bundle contains its truthful provider,
model, locality, drafting identity, and creation time; proposed events grouped
by local segment; one story; and one basket.

The importer validates the entire bundle, locally segments the selected private
transcript, verifies every cited span, and preflights all destinations before
writing. It then creates one immutable `agent_bundle_v1` run containing the
canonical finalized bundle and writes linked events, story, and basket with
`review_status: unreviewed`. The shared run is truthful for this combined agent
output; export continues to preserve distinct story and basket provenance
blocks even when their values are the same.

Interactive-agent mode makes no direct provider SDK/API call. A cloud coding
agent is recorded as `remote` unless its on-device model locality is verifiable.
The direct API route is paused pending a separate hardening slice for enforced
provider-call/retry limits and a redacted attempt ledger. It must not be used
for real material in the interim.

## Consequences

- Interactive and direct-API paths converge on the same private records and
  export contract, rather than maintaining a second story format.
- A valid bundle is not a truth or quality judgement; local span validation is
  still the only content check, as required by ADR-0008.
- Provider handling remains governed by [ADR-0009](ADR-0009-model-provider-boundary.md),
  and local inspection/publication boundaries remain governed by
  [ADR-0010](ADR-0010-local-analysis-publication-boundary.md).
- The importer cannot independently prove a bundle's claimed provider metadata.
  Truthful provenance is an operator responsibility, made explicit rather than
  defaulted or inferred from API-key absence.
- Canonical identity mapping is not added to `agent-bundle-v1`. It is an
  independent private sidecar; a future combined payload requires
  `agent-bundle-v2` (ADR-0012).
