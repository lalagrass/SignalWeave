# Product definition

## Purpose

SignalWeave turns recurring private research inputs into an evolving set of
stories, each carrying a basket of instruments that another tool can track.
A story is a hypothesis about a mechanism, not a recommendation, and not a claim
to be true.

## Research loop

```text
private source → story + wide basket → layer 1 tracks the basket → basket churns
```

The records are machine-authored. The judge is not a reviewer reading cards; it
is the market, over time, plus what later sources say. See
[ADR-0008](decisions/ADR-0008-machine-authored-records-and-pass-through-gate.md).

Two input lenses feed the same loop:

- **Transcript lens:** read a long conversation into groups, story context, and
  market sentiment, then widen into a basket of possibly-implicated instruments.
- **Post lens:** start from an observed instrument, infer one or more candidate
  themes, and grow each into its own story and its own basket. Candidate stories
  are tracked in parallel and compete; two candidates that produce the same
  basket are the same story for tracking purposes and are merged.

## Start wide, then prune

When a story is not yet clear, the basket starts deliberately wide — anything
plausibly implicated goes in. Being wrong at the start is the expected state,
not a defect. Membership then changes over time on three signals:

1. A later source states the story more specifically, narrowing it.
2. Earnings or news confirms or denies a name's exposure.
3. A name in the basket behaves unlike the rest of the basket. Layer 1 computes
   this for free. It flags a name to look at; it never decides truth and never
   ranks.

A story whose basket and strength have both been unchanged for several weeks is
marked `parked`.

## Core records

| Record | Contains | Does not contain |
| --- | --- | --- |
| Source locator | private document id and local offset | public source name or raw text |
| Event | neutral summary, date, evidence type, cited span | long quotation |
| Story | mechanism, groups, sentiment, open questions | a price-derived verdict |
| Basket | instruments, any market, dated membership history with reasons | weights, ordering, a composite score |
| Run | model id, method version, verbatim output | anything that cannot be re-read later |

## First usable screen

One page per story: the story context read out of the source, the basket, and
the basket's relative strength from layer 1. Rendered by MarketPulse, which owns
price; SignalWeave exports the story and the basket and never fetches a price.

## Success criterion

After importing one new private document, the pipeline produces that page
unattended, and the reader can say what story is being told and whether the
basket is getting stronger or weaker — without opening the source material or
any YAML.
