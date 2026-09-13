---
name: signalweave-transcript
description: Process, ingest, or analyze a private SignalWeave transcript through an interactive-agent bundle or an explicitly authorized direct provider API run.
---

# SignalWeave transcript processing

Use this skill when the user asks to process, ingest, or analyze a SignalWeave
transcript. Read `docs/transcript-processing.md` before acting.

Never reproduce transcript passages, cited spans, or source-specific findings
in terminal output, tracked files, reviews, progress updates, or handoffs. Keep
bundles and all generated records in ignored private zones.

## Choose the ingestion path

Use `interactive-agent` mode when the current agent can inspect the selected
private transcript and produce a private `agent-bundle-v1`. Record the agent's
actual provider, model id, and locality in the bundle. A cloud coding agent is
`remote` unless on-device execution is verifiable. No project API key or direct
SDK call does not mean local inference. Validate the finished bundle through
`import-agent-bundle`; do not manually create its derived records.

Before producing an interactive bundle, read `methods/agent_bundle_v1.md` and
the three methods it composes: `methods/propose_v1.md`,
`methods/story_v1.md`, and `methods/basket_v2.md`. The bundle remains v1 and
contains only its existing `basket.instruments` form. If canonical venue/symbol
identity is needed for export v2, create a separate private
`identifier-mapping-v1` bundle under its own method/provenance; do not insert
mapping fields into an existing `agent-bundle-v1`. Read
`methods/identifier_mapping_v1.md`, write the strict private JSON bundle from
`docs/contracts/identifier-mapping-bundle-v1.md`, then import it with
`signalweave import-identifier-mapping`. Never manually create the mapping run
or sidecar.

The direct-provider `run-pipeline` path is paused for real material pending
provider-call and retry limits plus a redacted attempt ledger. Do not select it
even when a credential and source-disclosure/cost authorization exist; use the
interactive-agent path until a dedicated hardening sprint re-enables it.

For either mode, report only safe counts, validation outcomes, provenance
metadata, and ignored output locations. Before any commit or handoff, run the
repository publication check and ensure no private output is staged.
