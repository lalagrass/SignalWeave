# Method: propose_v1

Used by the candidate-proposer step (`signalweave.propose`) once per transcript
segment. This file contains no source text — it is filled in with one
segment's text at call time and is never itself committed with source content.

## Instructions to the model

You are reading one paragraph from a private research transcript. Propose zero
or more candidate observations drawn only from this paragraph. Do not use
outside knowledge of the speaker, company, or market. Do not decide whether an
observation is correct — a later, separate process is responsible for that;
your only job is to name what was said and quote exactly where.

For each candidate, return a JSON object with these fields:

- `kind`: one of `evidence`, `observation`, `catalyst`, `counterargument`.
- `summary`: a short, neutral paraphrase (not a quotation) of what was said,
  at most 600 characters.
- `uncertainty`: one of `low`, `medium`, `high` — your confidence that this
  paraphrase is a fair reading of the paragraph.
- `cited_span`: the exact, verbatim substring of the paragraph that this
  candidate is drawn from. It must be copied character-for-character from the
  input — an invented or paraphrased span will be rejected.
- `claims`, `mechanisms`, `counterarguments` (optional): short string lists,
  each entry a distinct sub-point.

Return a JSON array of these objects, or an empty array `[]` if the paragraph
contains nothing worth surfacing. Return nothing else — no prose, no
markdown fencing, no commentary.

## Input template

```
<segment>
{segment_text}
</segment>
```
