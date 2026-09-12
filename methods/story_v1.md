# Method: story_v1

Used by the story-draft step (`signalweave.propose`) once per pipeline run, on
the neutral summaries already extracted by `propose_v1` — never on raw source
text. This file contains no source text.

## Instructions to the model

You are given a list of neutral, already-extracted observation summaries from
one research document. Draft a single story: a hypothesis about a mechanism
that ties these observations together. This is a starting hypothesis, not a
verdict — being wrong or too broad at this stage is expected, not a defect.

Return a single JSON object with these fields:

- `mechanism`: one paragraph stating the hypothesis — what is claimed to
  cause what, and why these observations are evidence for it.
- `open_question`: the single most important thing that would need to become
  clearer to judge this hypothesis.
- `invalidation_conditions`: a JSON array of at least one short string, each
  stating a concrete condition that would make this hypothesis wrong.
- `groups`: a JSON array of at least one short label naming the categories of
  instruments this mechanism plausibly touches (e.g. "upstream suppliers",
  "direct competitors") — not specific tickers yet.
- `market_sentiment`: one short sentence describing the direction and
  strength of sentiment expressed toward this mechanism in the source
  material (e.g. "cautiously positive on near-term demand").

Return nothing else — no prose outside the JSON object, no markdown fencing.

## Input template

```
<observations>
{observation_summaries}
</observations>
```
