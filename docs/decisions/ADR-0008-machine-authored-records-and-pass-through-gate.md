# ADR-0008: Machine-authored records with a pass-through review gate

## Status

Accepted. Supersedes ADR-0005's premise that manual drafting is the primary
path, and amends the research boundary in `AGENTS.md`.

## Context

The design to date required a human to author every free-text field: candidate
summaries, mechanisms, open questions, invalidation conditions, baskets. The
roadmap went further and gated an AI proposer on twenty hand-written candidate
summaries, to serve as both a style reference and an evaluation set.

There is no such human. The team is two engineers with no investment-research
background. The gate therefore never passes, the proposer never gets built, and
the tool stays permanently in the only mode nobody can sustain. That is a
deadlock, not rigour.

The gate existed to stop a machine promoting its own proposals. That concern is
real but it was aimed at the wrong risk. Under the method actually being used —
start with a deliberately wide basket and prune it as later sources and earnings
arrive — a wrong instrument at the start is the expected state, not a defect.
The question "is this card correct" is not the question the product answers.

## Decision

Records are machine-authored end to end. The review gate stays in the schema and
is set to pass-through: no record waits for a human.

Every record carries, without exception:

- `review_status: unreviewed` — never `accepted`, since nobody accepted it.
- `drafted_by` — which agent or model wrote the text (ADR-0007).
- the id of the run that produced it.

A record that was never judged must never be indistinguishable from one that
was. This keeps the option of adding real review later, selectively, without
re-running anything and without retroactively guessing which records were sound.

The only content check the pipeline performs is mechanical: the character span a
card cites must verifiably exist in the source. That catches invented locators
and fabricated quotes without a model call and without expertise. It does not
catch bad reasoning, and nothing cheap does.

Manual drafting (`draft-event`) remains available as a fallback and is no longer
the primary path.

## Consequences

- The twenty-hand-written-card gate is void. The proposer is built now.
- Quality is not asserted at write time. It is observed later, from basket churn
  and from what layer 1 shows about the basket's strength.
- No command in this project may print a number claiming a record is good.
  Cross-model agreement in particular is not a quality signal: current evaluation
  work finds that exact-match agreement overstates chance-corrected agreement by
  34–41 points, and that high test–retest reliability coexists with severe bias.
  Reproducibility does not imply validity. Agreement may be used to route
  attention to disagreements; it may never be reported as a score.
- `AGENTS.md`'s "a reviewer alone accepts a card" is replaced by the stamping
  rule above. The privacy boundary is unchanged.
- Adding review back is a later, evidence-driven decision: put a gate only where
  the record shows the pipeline is unreliable. That evidence does not exist yet
  and cannot be produced before the pipeline runs.
