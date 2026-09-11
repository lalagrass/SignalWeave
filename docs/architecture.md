# Architecture

## Design principle

SignalWeave separates source material, neutral observations, and causal
interpretation so that each research claim can be revisited without exposing
the original source.

```text
data/raw/ → extraction → data/inbox/ → human review → data/reviewed/
                                                   ├── events/
                                                   └── threads/
```

## Storage zones

| Zone | Git status | Purpose |
| --- | --- | --- |
| `data/raw/` | ignored | Original transcripts and observed posts. |
| `data/inbox/` | ignored | Candidate event cards that still need review. |
| `data/private/` | ignored | Identity maps, private annotations, and worklogs. |
| `data/reviewed/events/` | tracked when safe | De-identified, accepted observations. |
| `data/reviewed/threads/` | tracked when safe | Append-only hypothesis updates. |

## Records

### Candidate event

A proposed, neutral observation extracted from one source. It must include a
stable locator, a dated summary, and uncertainty. It may suggest thread links;
it cannot create or merge them.

### Reviewed event

A candidate event accepted and, where needed, de-identified by a reviewer.
It preserves the original candidate's locator and review decision.

### Thread

A human-owned hypothesis about a mechanism. It contains dated updates,
supporting evidence, counter-evidence, open questions, invalidation conditions,
and a review date. It never stores a price-derived verdict.

## Modules planned

| Module | Responsibility | Status |
| --- | --- | --- |
| `public_check` | Prevent accidental publication of private material. | shipped |
| `schema` | Validate event and thread records. | next |
| `extract` | Produce candidate cards with locators and uncertainty. | planned |
| `review` | Accept, reject, keep unlinked, or link a candidate. | planned |
| `threads` | Append reviewed evidence to human-owned hypotheses. | planned |
| `persona` | Derive evidence-backed research prompts from public corpus. | deferred |

## AI boundary

An AI integration must return structured candidate data, include source
locators, preserve uncertainty, and remain reviewable. It must not silently
write reviewed records or represent a research persona as a person's current
view.
