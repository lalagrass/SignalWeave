"""A story's basket: the instruments it implicates (milestone 2 shape).

One basket per story — a flat instrument list, not the retired
if_true/if_false/either_way split (see `docs/specs/thread-exposure-v0.md`'s
DO-1, superseded by `docs/specs/milestone-2-v0.md`'s "Basket shape"). Dated
membership history and pruning are milestone 3; for M2 a basket is written
once by the pipeline run that drafted its story and is not revised in place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml

from signalweave.schema import IDENTIFIER


# An instrument identifier is market-facing, not one of SignalWeave's own ids:
# a basket has to name something a price-tracking consumer can resolve against
# real market data (`2330`, `AAPL`, `BRK.B`), which `schema.IDENTIFIER` — the
# lowercase rule for this project's internal ids — cannot express. Hence a
# separate pattern here, and IDENTIFIER left untouched for thread_id,
# drafted_by, and run_id (methods/basket_v2.md).
INSTRUMENT = re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$")


REQUIRED_FIELDS = frozenset(
    {
        "thread_id",
        "instruments",
        "review_status",
        "drafted_by",
        "run_id",
        "created_at",
    }
)


class BasketValidationError(ValueError):
    """Raised when a basket record does not meet its contract."""


@dataclass(frozen=True)
class Basket:
    """The wide, machine-drafted instrument list for one story."""

    thread_id: str
    instruments: tuple[str, ...]
    review_status: str
    drafted_by: str
    run_id: str
    created_at: datetime

    @classmethod
    def from_mapping(cls, record: dict[str, Any]) -> "Basket":
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            raise BasketValidationError(f"missing required field(s): {', '.join(missing)}")
        unknown = sorted(record.keys() - REQUIRED_FIELDS)
        if unknown:
            raise BasketValidationError(f"unknown field(s): {', '.join(unknown)}")

        review_status = _non_empty_string(record["review_status"], "review_status")
        if review_status != "unreviewed":
            raise BasketValidationError("review_status must be 'unreviewed'")

        return cls(
            thread_id=_identifier(record["thread_id"], "thread_id"),
            instruments=_instrument_list(record["instruments"]),
            review_status=review_status,
            drafted_by=_identifier(record["drafted_by"], "drafted_by"),
            run_id=_identifier(record["run_id"], "run_id"),
            created_at=_datetime(record["created_at"], "created_at"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "instruments": list(self.instruments),
            "review_status": self.review_status,
            "drafted_by": self.drafted_by,
            "run_id": self.run_id,
            "created_at": self.created_at.isoformat(),
        }


def create_basket(
    *,
    thread_id: str,
    instruments: list[str],
    drafted_by: str,
    run_id: str,
    created_at: datetime | None = None,
) -> Basket:
    """Create a basket. `review_status` is always `unreviewed` (ADR-0008):

    nothing has judged this membership list, so nothing may claim otherwise.
    An empty basket is permitted — emptiness is a finding, not an error.
    """
    return Basket.from_mapping(
        {
            "thread_id": thread_id,
            "instruments": instruments,
            "review_status": "unreviewed",
            "drafted_by": drafted_by,
            "run_id": run_id,
            "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        }
    )


def write_basket(basket: Basket, threads_directory: Path) -> Path:
    """Write a story's basket once. Refuses to overwrite an existing one.

    Revising membership over time (milestone 3) is a different, dated,
    append-only mechanism not built yet; a second run must not silently
    clobber the first.
    """
    thread_directory = threads_directory / basket.thread_id
    if not (thread_directory / "thread.yaml").is_file():
        raise FileNotFoundError(f"thread does not exist: {basket.thread_id}")
    path = thread_directory / "basket.yaml"
    if path.exists():
        raise FileExistsError(f"basket already exists: {path}")
    path.write_text(
        yaml.safe_dump(basket.to_mapping(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def load_basket(thread_directory: Path) -> Basket:
    """Load one story's basket without changing it."""
    path = thread_directory / "basket.yaml"
    try:
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise BasketValidationError(f"invalid YAML in {path}: {error}") from error
    if not isinstance(record, dict):
        raise BasketValidationError("basket record must be a YAML mapping")
    return Basket.from_mapping(record)


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise BasketValidationError(
            f"{field} must use lowercase letters, digits, and underscores, starting with a letter"
        )
    return value


def _instrument(value: Any) -> str:
    if not isinstance(value, str) or not INSTRUMENT.fullmatch(value):
        raise BasketValidationError(
            "instruments must be alphanumeric, optionally separated by '.', '_', or '-'"
        )
    return value


def _instrument_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise BasketValidationError("instruments must be a list")
    return tuple(_instrument(item) for item in value)


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BasketValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise BasketValidationError(f"{field} must be an ISO-8601 timestamp")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise BasketValidationError(f"{field} must be an ISO-8601 timestamp") from error
    if timestamp.tzinfo is None:
        raise BasketValidationError(f"{field} must include a timezone")
    return timestamp
