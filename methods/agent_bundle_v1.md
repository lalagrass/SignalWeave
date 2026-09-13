# Method: agent_bundle_v1

This tracked method describes the private interactive-agent bundle imported by
`signalweave.agent_bundle`. It composes the current candidate, story, and
basket methods without changing the immutable `agent-bundle-v1` JSON shape.
It contains no source text.

## Required composition

1. Read and apply `methods/propose_v1.md` separately to each supplied local
   transcript segment. Preserve exact cited spans in the resulting event
   proposals.
2. Read and apply `methods/story_v1.md` to the resulting neutral summaries.
3. Read and apply `methods/basket_v2.md` to that story. Its output remains
   `basket.instruments` in `agent-bundle-v1`; the bundle does not contain
   canonical identity mappings.

Return the exact `agent-bundle-v1` JSON contract expected by the importer:
truthful provider/model/locality provenance, segment-grouped event proposals,
one story, and one `basket.instruments` list. Do not add mapping fields,
prices, scores, rankings, or commentary.

Canonical venue/symbol identity is intentionally a separate private,
append-only `identifier-mapping-v1` record bound to the resulting basket
snapshot. If an interactive agent must produce that record in the same native
payload in the future, introduce `agent-bundle-v2`; do not extend this v1
bundle silently.
