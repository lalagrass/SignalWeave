---
name: signalweave-sprint
description: Plan, implement, review, and hand off one SignalWeave sprint when asked to run, start, continue, or plan the next sprint. Use only inside the SignalWeave repository; do not use for isolated questions or tiny edits that are not sprint work.
---

# SignalWeave Sprint

Run one small vertical slice from product contract through verified handoff. The
user's request takes precedence over this workflow. Follow the repository's
`AGENTS.md` privacy, research, and verification boundaries throughout.

## Establish the working copy

1. Resolve the repository root with Git and work only there. Confirm the remote
   identifies SignalWeave, report the current branch and dirty state, and preserve
   unrelated changes.
2. If the current directory is not a Git checkout of SignalWeave, stop before
   editing and identify the mismatch. Never copy `.git` metadata between folders.
3. If the current request includes commit or push and the checkout is on an
   integration branch, create a focused `codex/<scope>` branch before editing.
4. Do not read private-source contents to choose or plan engineering work.

## Form the sprint contract

1. Read `AGENTS.md`, `docs/roadmap.md`, `docs/architecture.md`, and only the specs
   and ADRs relevant to the current milestone.
2. Delegate a read-only scope review to the `product_owner` custom agent when the
   request is to plan or run a sprint. Ask it for the observable outcome, scope,
   non-goals, acceptance criteria, dependencies, and largest risk.
3. Reconcile its recommendation with the user's explicit request and the current
   repository state. The main agent owns the final contract. If a missing product
   choice would materially change the result, stop and ask one focused question.

## Implement with one writer

1. The main agent is the only writer. It may delegate independent read-only
   exploration, but must not assign overlapping file edits to multiple agents.
2. Build the smallest vertical slice that satisfies the sprint contract. Preserve
   public interfaces unless the contract explicitly changes them.
3. Add or update tests for behavior and failure paths. Record a durable design
   choice in an ADR only when future work would otherwise reopen the decision.
4. Keep source-specific notes in the ignored private worklog, never in tracked
   handoff documents.

## Verify and review

1. Run focused checks while implementing.
2. Run the full repository verification required by `AGENTS.md` before handoff.
3. After implementation, delegate two independent read-only reviews, which may
   run in parallel. Include the agreed sprint contract in each review request:
   - `reviewer` checks correctness, regressions, contracts, and tests.
   - `privacy_reviewer` checks repository boundaries without reading private data.
4. Fix blocking findings as the single writer, rerun affected checks, and ask for
   one final review pass only when the fix materially changes the reviewed design.
   Keep non-blocking follow-ups visible instead of silently widening the sprint.

## Leave durable state

1. Update `docs/roadmap.md` with the observable result, exact verification, and
   the next scoped item. Keep sensitive run details in the private worklog.
2. Summarize the completed outcome, verification, review findings, remaining
   risks, and the recommended next slice.
3. Do not commit, push, open a pull request, or merge unless the user explicitly
   requests that Git action. When requested, use the focused feature branch
   created at the start unless the user names another branch, and stop before
   merge unless merge is also explicitly requested.
