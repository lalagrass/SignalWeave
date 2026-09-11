# Product definition

## Purpose

SignalWeave turns recurring private research inputs into an evolving, auditable
set of threads. A thread is a human-owned hypothesis about a mechanism, not a
machine-made recommendation.

## Research loop

```text
private source → candidate event → human review → dated thread update → revisit
```

Two input lenses feed the same loop:

- **Transcript lens:** split a long conversation into claims, mechanisms,
  catalysts, counterarguments, and affected entities.
- **Post lens:** start with an observed company/event, then propose an upstream
  driver, downstream effects, alternative explanations, and discriminating
  evidence.

Both lenses may suggest links. Neither can merge a thread or declare an outcome
without a reviewer.

## Core records

| Record | Contains | Does not contain |
| --- | --- | --- |
| Source locator | private document id and local offset | public source name or raw text |
| Event | neutral summary, date, evidence type | long quotation |
| Thread | mechanism, claims, open questions, review date | a price-derived verdict |
| Exposure | possible beneficiaries, alternatives, constraints | a composite score |

## First usable screen

The Inbox shows proposed event cards. For each card, the reviewer can choose:
`link to thread`, `create thread`, `keep unlinked`, or `discard`. Accepted
updates appear on a thread timeline with supporting and counter evidence kept
separate.

## Success criterion

After importing one new private document, a reviewer can turn its useful ideas
into traceable thread updates within ten minutes, without exposing the original
material to the repository.

