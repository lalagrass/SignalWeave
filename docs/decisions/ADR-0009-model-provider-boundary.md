# ADR-0009: Raw source may reach a model provider, recorded per run

## Status

Accepted.

## Context

The privacy contract to date protects the *repository*: raw material is
Git-ignored, tracked files carry neutral identifiers, and `public-check` refuses
to run unconfigured (ADR-0006). It has never said anything about a model
provider, because until now no provider was called.

Machine-authored records (ADR-0008) mean source text is sent to a model. That is
a new boundary crossing and must be decided explicitly rather than happening as
a side effect of adding a proposer.

The material in play is a public podcast and public posts. The contract's real
promise is "this never gets committed to a public repo", not "this never leaves
the laptop". A small local model would produce output poor enough to undermine
the only thing being built — a pipeline whose output is worth looking at.

## Decision

Remote model providers are allowed.

- Every run records `provider`, `model_id`, and `model_locality`
  (`local` | `remote`).
- Sources carry a privacy tier in configuration. A source marked local-only
  refuses to run against a remote provider, and that refusal is an error, not a
  warning.
- The repository boundary is unchanged: nothing about a provider call relaxes
  what may be committed. Prompts and method files are tracked and must contain no
  source text.
- Source text is still never written to a log line or an error message, and
  `public-check` still governs what may be published.

## Consequences

- Raw transcripts leave the machine for the default (remote) tier. That is a
  deliberate, recorded choice, visible per run rather than implied.
- Switching a source to local-only is a configuration change, not a code change,
  so a genuinely sensitive source can be added later without redesign.
- Run records state which provider saw which document, so the question "what left
  this machine, and when" has an answer that does not depend on memory.
