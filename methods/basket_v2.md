# Method: basket_v2

Used by the basket-draft step (`signalweave.propose`) once per pipeline run,
on the story just drafted by `story_v1` — never on raw source text. This file
contains no source text.

Supersedes `basket_v1` for one reason: `basket_v1`'s plain lowercase slugs
(`"tsmc"`, `"hon_hai"`) are not something any price-tracking consumer can look
up — the seam decision requires SignalWeave's export to hand MarketPulse
identifiers it can resolve against real market data, and a name is not that.
`basket_v1`'s own baskets are left as they were drafted (a basket is written
once and not revised in place, per `docs/specs/milestone-2-v0.md`) — this
fixes the method for baskets drafted from here on, not retroactively.

## Instructions to the model

You are given one story: a mechanism, its implicated groups, and its market
sentiment. Widen this into a basket of specific, publicly tradeable
instruments that are plausibly implicated by this mechanism.

Start deliberately wide. Anything plausibly connected to a named group belongs
in the basket — being wrong about a specific name at this stage is expected
and will be pruned later by what the market and later sources say, not by you.
Do not rank, weight, or order the instruments; do not attach a score or a
count of how confident you are in each one. An empty basket is a valid answer
when nothing in the story maps to a specific, nameable instrument — say so by
returning an empty list, not by inventing a name to fill it.

**Identifier form, for each instrument:** if it is listed on a public stock
exchange and you know its exchange ticker or quote code, return that code —
for example `"2330"` for TSMC's Taiwan-listed shares, not `"tsmc"`; `"AAPL"`
for Apple's US-listed shares. Use a plain lowercase name only when you do not
know a specific tradeable code, or the thing itself is not directly listed
(a private company, a raw material, a supply-chain step rather than a
company, a subsidiary that trades only as part of its parent). Do not guess a
code you are not confident in — an unresolved plain name is a valid, honest
answer; a wrong code is not.

Return a single JSON object: `{"instruments": [...]}`, a JSON array of plain
identifiers — exchange codes and lowercase names both allowed, mixed as
described above. Return nothing else — no prose, no markdown fencing.

## Input template

```
<story>
mechanism: {mechanism}
groups: {groups}
market_sentiment: {market_sentiment}
</story>
```
