"""Emit story and basket for layer 1 (MarketPulse). No price, no ranking.

Command surface reused from `docs/specs/thread-exposure-v0.md` DO-2
(thread/story id, review date, overdue flag) with the milestone-2 basket
shape: one flat instrument list per story, not a three-way split.

Includes `mechanism`, `groups`, and `market_sentiment` — the same fields
`show-thread` already prints — read straight from the thread, unreworded.
These are model-synthesized from already-abstracted candidate events, never
raw transcript text, so exporting them carries no privacy issue; only raw
source text must never leave SignalWeave, and that is unchanged (see
`docs/specs/milestone-2-v0.md` scope item 5's correction note). Deliberately
excluded: `open_question` and `invalidation_conditions` — not asked for, and
not needed by anything reading this export today.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from signalweave.basket import load_basket
from signalweave.threads import list_thread_ids, load_thread


def export_baskets(threads_directory: Path, *, as_of: date) -> list[dict[str, Any]]:
    """Build one export entry per story. Nothing here reads source text."""
    entries: list[dict[str, Any]] = []
    for thread_id in list_thread_ids(threads_directory):
        thread_directory = threads_directory / thread_id
        thread = load_thread(thread_directory)
        basket = load_basket(thread_directory)
        entries.append(
            {
                "thread_id": thread.thread_id,
                "review_date": thread.review_date.isoformat(),
                "overdue": thread.review_date < as_of,
                "basket": list(basket.instruments),
                "mechanism": thread.mechanism,
                "groups": list(thread.groups),
                "market_sentiment": thread.market_sentiment,
            }
        )
    return entries


def write_export(entries: list[dict[str, Any]], out_path: Path, *, as_of: date) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(
            {"as_of": as_of.isoformat(), "stories": entries},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return out_path
