# Development workflow

SignalWeave uses the repository as its durable memory and one Codex task as the
sprint orchestrator. Product scope, implementation, and review do not need to be
copied between separate chats.

## Source of truth

- `docs/roadmap.md` says which outcome is next and records verified progress.
- `docs/specs/` defines an observable slice when the roadmap needs more detail.
- `docs/decisions/` preserves decisions future work must not rediscover.
- Git diffs and tests show what changed; ignored private worklogs hold
  source-specific context.

## Agent roles

- The main task owns the sprint contract, all file edits, verification, and
  handoff.
- `product_owner` is a read-only scope critic used at sprint boundaries.
- `reviewer` is a read-only correctness and regression reviewer.
- `privacy_reviewer` is a read-only boundary reviewer and never opens private
  data.

One writer avoids merge conflicts and ambiguous ownership. Review agents are
temporary perspectives, not separate sources of project truth.

## Starting work

Open the SignalWeave Git clone as the Codex project (not a copied output folder),
then ask:

> Run the next SignalWeave sprint.

The repository skill at
`.agents/skills/signalweave-sprint/SKILL.md` scopes the work, invokes the relevant
review roles, verifies the result, and updates the handoff. Add “commit and push”
only when that external Git action is desired. A human still decides whether to
merge.

Use `dev` as the integration branch and short-lived `codex/<scope>` branches for
sprint changes. Keep `main` at milestone-quality states.
