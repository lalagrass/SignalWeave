# Spec: transcript navigation v0

**Milestone:** 2 — real material in, baskets out
**Roadmap item:** transcript navigation v0
**Appetite:** one session. One new command, three friction fixes, one ADR.

## Why this now

The loop works on a one-paragraph post. It does not work on the material the
product exists for: a podcast transcript of 200+ lines. `draft-event --segment N`
requires knowing N in advance, and nothing can show what segment N is, because
ADR-0003 forbids echoing source text. On a long transcript a reviewer must guess
positions, and guessing is not review.

The walkthrough's friction list names three further rough edges, all cheap.

## DO-1 — segment index

```bash
uv run --no-sync signalweave list-segments path/to/private.md --source source_a --document-id doc_2026_001
```

Print one line per segment: position, locator, and character count. No text, no
excerpt, no first words. This lets a reviewer with the file open in an editor map
what they are reading onto a position number.

## DO-2 — decide the echo rule, then implement it

ADR-0003 currently forbids printing source text at all. That rule was written to
keep raw text away from logs, tracked files, and an AI provider. It also blocks
the owner of the material from seeing their own paragraph in their own terminal,
which is what makes a long transcript unworkable.

Proposed narrowing — **the PO must confirm before this is implemented**:

> Source text may be printed to an interactive terminal on explicit human
> request. It must never be written to a file, never appear in an error message
> or log line, never be included in command output that is redirected or piped
> without the flag being given again, and never be passed to a proposer.

If accepted, add `--show` to `list-segments` and to `draft-event`, printing the
selected segment only. Supersede the relevant clause of ADR-0003 with a new ADR
that states the narrowing and its boundary; do not silently edit ADR-0003.

If the PO rejects the narrowing, DO-2 is dropped and DO-1 stands alone. Do not
implement a middle option such as a truncated preview — a first sentence is still
source text, and a partial rule is harder to reason about than either whole one.

## DO-3 — friction fixes

1. `append-thread-update` takes a review YAML path. Accept `--review-id` and
   resolve it against `data/inbox/reviews/`; keep the path form working.
2. `--thread` is validated only indirectly, so a typo fails late with a message
   about the review rather than about the thread. Check that the thread directory
   exists first and fail with a message naming the unknown thread id.
3. `--invalidation-condition` is repeatable but `--help` does not say so. Say so,
   here and on any other repeatable flag.

## Acceptance

1. The documented verification commands pass.
2. One real podcast transcript is run end to end by a human reviewer: at least
   three candidate cards drafted, filled and validated, at least one thread
   created, at least two updates appended, then read back with `show-thread`.
3. The elapsed time is recorded honestly, separating reading-and-thinking time
   from command time, in ignored `data/private/worklog/`. This run is the first
   real test of the ten-minute criterion: the reviewer, not the implementing
   agent, writes every free-text field. `drafted_by` must say so.
4. New friction goes to the same worklog and into the roadmap as the input to
   the next item.

## Out of scope

Exposure baskets, AI proposer, persona, reviewed-event promotion, market data,
any change to the review gate.
