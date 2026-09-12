# Method: basket_v1

Used by the basket-draft step (`signalweave.propose`) once per pipeline run,
on the story just drafted by `story_v1` — never on raw source text. This file
contains no source text.

## Instructions to the model

You are given one story: a mechanism, its implicated groups, and its market
sentiment. Widen this into a basket of specific, publicly tradeable
instruments (tickers or other plain market identifiers) that are plausibly
implicated by this mechanism.

Start deliberately wide. Anything plausibly connected to a named group belongs
in the basket — being wrong about a specific name at this stage is expected
and will be pruned later by what the market and later sources say, not by you.
Do not rank, weight, or order the instruments; do not attach a score or a
count of how confident you are in each one. An empty basket is a valid answer
when nothing in the story maps to a specific, nameable instrument — say so by
returning an empty list, not by inventing a name to fill it.

Return a single JSON object: `{"instruments": [...]}`, a JSON array of plain
lowercase identifiers (letters, digits, underscores; e.g. `"tsmc"`,
`"asml"`). Return nothing else — no prose, no markdown fencing.

## Input template

```
<story>
mechanism: {mechanism}
groups: {groups}
market_sentiment: {market_sentiment}
</story>
```
