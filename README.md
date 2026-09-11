# SignalWeave

SignalWeave is a local, source-agnostic research-memory tool. It turns private
transcripts and posts into reviewable event cards and evolving research threads.
Market data may be attached as an independent observation; it never decides
whether a thread is true.

## What ships first

1. Keep source material private and local.
2. Produce candidate event cards in an inbox for human review.
3. Promote accepted cards into dated, append-only research threads.
4. Show each thread's evidence, counter-evidence, open question, and review date.

The product is deliberately not a trading system, a prediction engine, or an
automatic truth classifier.

## Privacy and publishing

Raw material, source identities, private aliases, API keys, and generated
excerpts must never be committed. Use neutral identifiers such as `source_a`,
`doc_2026_001`, and `thread_supply_constraint` in tracked files.

Before publishing, run:

```bash
uv run signalweave public-check
```

Add organisation- or source-specific terms to the untracked
`.signalweave/private_terms.txt` (copy the example file first). The command is
a guardrail, not a substitute for a human review.

See [the product definition](docs/PRODUCT.md) and [privacy contract](docs/PRIVACY.md).

## Local setup

```bash
uv sync --no-editable
uv run --no-sync pytest
uv run --no-sync signalweave public-check
```

`--no-editable` keeps the command-line package importable in the current
workspace environment. Re-run the sync command after changing source files or
project metadata.
