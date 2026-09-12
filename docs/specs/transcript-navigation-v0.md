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

## DO-2 — implement the narrowed echo rule (decided)

ADR-0003 currently forbids printing source text at all. That rule was written to
keep raw text away from logs, tracked files, and an AI provider. It also blocks
the owner of the material from seeing their own paragraph in their own terminal,
which is what makes a long transcript unworkable.

The narrowing is decided. This is the rule, not a proposal:

> Source text may be printed only to an interactive terminal, only on explicit
> human request via `--show`, and only when standard output is a TTY. It must
> never be written to a file, never appear in an error message or a log line,
> never be included in output that is redirected or piped, and never be passed
> to a proposer.

Implementation requirements:

1. Add `--show` to `list-segments` and to `draft-event`. Each prints the text of
   the one selected segment and nothing else — no surrounding label repeats
   another segment's content, no batch mode.
2. Before printing anything from `--show`, check whether stdout is a TTY
   (`sys.stdout.isatty()`). If it is not — piped, redirected to a file,
   captured by a test harness, anything non-interactive — refuse the whole
   command: print a refusal message that contains no source text (e.g.
   "refusing --show: stdout is not a terminal") and exit non-zero. The check is
   on the destination, not on whether `--show` was passed; a command run
   without `--show` already prints no text and needs no such check.
3. Audit every existing exception message and print statement in `extract.py`
   and `cli.py` that touches a `TranscriptSegment`. None may interpolate
   `segment.text` or any substring of it — only `position` and
   `source_locator` are safe to name in an error.
4. `--show`'s output is a dead end: it must never feed back into
   `extract_candidates` or a `CandidateProposer` call. This does not change the
   proposer's own existing access to `segment.text` inside `extract_candidates`
   (ADR-0003's original design) — that path is untouched; `--show` is a
   separate, human-only display path that must never merge with it.

**New ADR, new number, no edit to ADR-0003.** Write `ADR-0008` (the next unused
number — do not reuse or renumber `ADR-0001` through `ADR-0007`) stating this
narrowing and quoting the specific clause of ADR-0003's Consequences it
overrides ("never prints its contents"). `ADR-0003`'s file is not touched — not
its Decision text, not its Consequences, not even its Status line. It stays the
unedited record of the original decision; ADR-0008 is the only place the
narrowing is written down, alongside this spec and the roadmap. This matches
how ADR-0007 handled a previous correction: supersede with a new record,
never patch the old one in place.

Do not implement a middle option such as a truncated preview — a first sentence
is still source text, and a partial rule is harder to reason about than either
whole one.

## DO-3 — friction fixes

1. `append-thread-update` takes a review YAML path. Accept `--review-id` and
   resolve it against `data/inbox/reviews/`; keep the path form working.
2. `--thread` is validated only indirectly, so a typo fails late with a message
   about the review rather than about the thread. Check that the thread directory
   exists first and fail with a message naming the unknown thread id.
3. `--invalidation-condition` is repeatable but `--help` does not say so. Say so,
   here and on any other repeatable flag.

## Acceptance

Acceptance for this spec is synthetic only. It is done when:

1. New or updated tests, run against synthetic transcript fixtures (no real
   podcast material), cover: `--show` printing exactly the selected segment's
   text and nothing else; refusal with no source text in the message when
   stdout is not a TTY; `--review-id` resolving against
   `data/inbox/reviews/` with the path form still accepted; an unknown
   `--thread` failing with a message naming that thread id, before any
   review-content check runs; `--help` documenting every repeatable flag
   (`--invalidation-condition` and any other that takes `action="append"`).
2. The documented verification commands pass:
   `uv run --no-sync pytest` and `uv run --no-sync signalweave public-check`.

## Not part of this spec's acceptance

Running one real podcast transcript end to end — at least three candidate
cards drafted and validated, one thread created, two updates appended, read
back with `show-thread`, with `drafted_by` recording that a human wrote every
free-text field — is the PO's own walkthrough. The PO runs it themselves,
separately, after this spec ships; it is the first real test of the
ten-minute criterion, and its elapsed time and new friction go into
`data/private/worklog/` and the roadmap from that run. It is not something
the implementing agent does, and it does not gate this item's completion.

## Out of scope

Exposure baskets, AI proposer, persona, reviewed-event promotion, market data,
any change to the review gate.
