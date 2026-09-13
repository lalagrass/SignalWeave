---
name: signalweave-sprint
description: Plan, execute, review, or explicitly deliver one SignalWeave sprint. Use inside the SignalWeave repository for requests to plan the next sprint, start/run/continue sprint work, or merge/push a verified sprint; do not use for isolated questions or tiny edits. Planning alone never authorizes implementation.
---

# SignalWeave Sprint

Run one small vertical slice from product contract through verified handoff. The
user's request takes precedence over this workflow. Follow the repository's
`AGENTS.md` privacy, research, and verification boundaries throughout.
This workflow requires a SignalWeave Git checkout. Custom product-owner and
review agents are preferred when available; disclosed local fallbacks are below.

## Choose the engagement mode

Infer the narrowest mode authorized by the user's wording before changing state:

- **Plan/review mode** — for `plan`, `review`, `assess`, or `what next`. Inspect
  the repository and produce a sprint contract or review. Do not edit product
  code, create a branch, or commit unless the user explicitly asks to record the
  plan in the repository. Stop before the implementation sections below.
- **Run mode** — for `start`, `run`, `continue`, `implement`, or `fix` a sprint.
  Establish the working copy, form the contract, implement, verify, review, and
  leave a local committed checkpoint.
- **Delivery mode** — for an explicit request to commit, merge, push, or open a
  pull request for already verified work. Recheck the exact repository, branch,
  remote, clean/dirty state, and ancestry, then perform only the requested Git
  actions. Never force-push unless the user explicitly requests that destructive
  operation and the exact target has been verified.

When wording mixes modes, complete the work already authorized and ask only if
the unresolved choice would materially change the outcome.

## Establish the working copy

1. Resolve the repository root with Git and work only there. Confirm the remote
   identifies SignalWeave, report the current branch and dirty state, and preserve
   unrelated changes.
2. If the current directory is not a Git checkout of SignalWeave, stop before
   editing and identify the mismatch. Never copy `.git` metadata between folders.
3. In run mode, or in plan mode explicitly asked to record a plan, unless the
   user chooses another branch strategy, create or switch to a focused
   `codex/<scope>` branch before editing sprint files. Branch creation does not
   require separate commit or push authorization.
4. In run mode, if sprint work has already started on an integration branch,
   preserve the working tree and create the focused branch immediately, before
   further edits or commits. When a sprint spans repositories, use a focused
   branch in each repository and record the branch mapping in the handoff.
5. Local source inspection is allowed when it is relevant to the requested
   outcome. Use targeted reads, hashes, or comparisons as appropriate, and keep
   source content and source-specific findings in ignored private zones.

## Form the sprint contract

Plan and run modes only. Delivery mode uses the already verified contract.

1. Read `AGENTS.md`, `docs/roadmap.md`, `docs/architecture.md`, and only the specs
   and ADRs relevant to the current milestone.
2. Delegate a read-only scope review to the `product_owner` custom agent when the
   request is to plan or run a sprint and that role is available. Ask it for the
   observable outcome, scope, non-goals, acceptance criteria, dependencies, and
   largest risk. If it is unavailable, perform the same review locally and state
   that the result was not independently delegated.
3. Reconcile its recommendation with the user's explicit request and the current
   repository state. The main agent owns the final contract. If a missing product
   choice would materially change the result, stop and ask one focused question.

## Implement with one writer

Run mode only.

1. The main agent is the only writer. It may delegate independent read-only
   exploration, but must not assign overlapping file edits to multiple agents.
2. Build the smallest vertical slice that satisfies the sprint contract. Preserve
   public interfaces unless the contract explicitly changes them.
3. Add or update tests for behavior and failure paths. Record a durable design
   choice in an ADR only when future work would otherwise reopen the decision.
4. Keep source-specific notes in the ignored private worklog, never in tracked
   handoff documents.

## Verify and review

Run mode only.

1. Run focused checks while implementing.
2. Run the full repository verification required by `AGENTS.md` before handoff.
3. After implementation, delegate two independent read-only reviews when those
   roles are available; they may run in parallel. Include the agreed sprint
   contract in each review request:
   - `reviewer` checks correctness, regressions, contracts, and tests.
   - `privacy_reviewer` checks repository and publication boundaries. It may
     inspect local private material when needed but must not reproduce it.
   If either role is unavailable, perform an explicit local pass for that concern
   and disclose that it was not an independent review.
4. Fix blocking findings as the single writer, rerun affected checks, and ask for
   one final review pass only when the fix materially changes the reviewed design.
   Keep non-blocking follow-ups visible instead of silently widening the sprint.

## Leave durable state

Run mode only. Delivery mode begins from the verified state left here.

1. Update `docs/roadmap.md` with the observable result, exact verification, and
   the next scoped item. Keep sensitive run details in the private worklog.
2. After required checks and reviews pass, stage only sprint-owned files, inspect
   the staged diff, and create scoped local commits. A verified sprint ends with
   local commit hashes unless the user explicitly asks to leave it uncommitted.
3. When work spans repositories, commit each repository separately. Never include
   unrelated pre-existing changes; report each repository's branch, commit hash,
   and remaining dirty state.
4. Summarize the completed outcome, verification, review findings, remaining
   risks, and the recommended next slice.
5. Do not push, open a pull request, or merge unless the user explicitly requests
   that external Git action. Stop before merge unless merge was separately and
   explicitly requested.
