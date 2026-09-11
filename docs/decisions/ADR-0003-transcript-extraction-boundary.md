# ADR-0003: Keep transcript segmentation private and extraction model-independent

## Status

Accepted

## Context

The product needs to process private transcripts before an AI provider has been
selected. Raw text must not leak into logs, tracked records, or a provider-
specific implementation. Candidate output must still obey the shared event
contract.

## Decision

Represent each transcript paragraph as an in-memory `TranscriptSegment` with a
stable local locator. Define a `CandidateProposer` protocol that receives one
segment and returns candidate mappings. The extraction boundary overwrites the
proposal's source, locator, and review status, then validates it as a
`CandidateEvent`. The default proposer emits no candidates.

The initial CLI supports only `--dry-run`. It reads a private file, reports
segment and candidate counts, and never prints its contents or writes cards.

## Consequences

- An AI provider can be added later without changing privacy or review rules.
- Extraction tests run entirely on synthetic text.
- Source text cannot reach an event record through undocumented fields.
- A later inbox-writing step must be explicitly designed and reviewed.
