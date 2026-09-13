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

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from signalweave.basket import load_basket
from signalweave.identifier_mapping import (
    load_active_identifier_mapping,
    mapping_provenance,
)
from signalweave.runs import load_run
from signalweave.threads import list_thread_ids, load_thread

SCHEMA_VERSION = 2

def _provenance(record: Any, runs_directory: Path) -> dict[str, str]:
    """Export record provenance with its method resolved from an immutable run."""
    run = load_run(runs_directory / f"{record.run_id}.yaml")
    return {
        "review_status": record.review_status,
        "drafted_by": record.drafted_by,
        "run_id": record.run_id,
        "method_version": run.method_version,
    }


def export_baskets(
    threads_directory: Path,
    runs_directory: Path,
    identifier_mappings_directory: Path,
    *,
    as_of: date,
) -> list[dict[str, Any]]:
    """Build one v2 export entry per story. Nothing here reads source text.

    Every v2 basket member comes from an independent, immutable identity
    mapping bound to the basket's exact run and timestamp.  A missing or
    ambiguous mapping is an export failure, never a name-resolution fallback.
    """
    entries: list[dict[str, Any]] = []
    for thread_id in list_thread_ids(threads_directory):
        thread_directory = threads_directory / thread_id
        thread = load_thread(thread_directory)
        basket = load_basket(thread_directory)
        mapping = load_active_identifier_mapping(identifier_mappings_directory, basket=basket)
        identifier_provenance = mapping_provenance(mapping, runs_directory)
        entries.append(
            {
                "thread_id": thread.thread_id,
                "review_date": thread.review_date.isoformat(),
                "overdue": thread.review_date < as_of,
                "mechanism": thread.mechanism,
                "groups": list(thread.groups),
                "market_sentiment": thread.market_sentiment,
                "provenance": _provenance(thread, runs_directory),
                "basket": {
                    "members": [member.to_mapping() for member in mapping.members],
                    "provenance": _provenance(basket, runs_directory),
                    "identifier_provenance": identifier_provenance.to_mapping(),
                },
            }
        )
    return entries


def write_export(
    entries: list[dict[str, Any]],
    out_path: Path,
    *,
    as_of: date,
    private_exports_directories: tuple[Path, ...],
    generated_at: datetime | None = None,
) -> Path:
    generated_at = generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        raise ValueError("generated_at must include a timezone")
    destination = out_path.resolve()
    if not any(_is_within(destination, directory.resolve()) for directory in private_exports_directories):
        raise ValueError(
            "export output must be under data/private/exports/ or "
            "MarketPulse/data/private/signalweave/"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        yaml.safe_dump(
            {
                "schema_version": SCHEMA_VERSION,
                "as_of": as_of.isoformat(),
                "generated_at": generated_at.isoformat(),
                "stories": entries,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return destination


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
