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

Use `direct-api` mode only when the user explicitly authorizes both disclosure
of that source to the chosen provider and its cost for this run. Then use
`run-pipeline` with the declared privacy tier. Do not select this path merely
because a credential exists.

For either mode, report only safe counts, validation outcomes, provenance
metadata, and ignored output locations. Before any commit or handoff, run the
repository publication check and ensure no private output is staged.
