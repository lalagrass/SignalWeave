"""Schemas for private, human-reviewable research records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Any

import yaml


class EventValidationError(ValueError):
    """Raised when a candidate event does not meet SignalWeave's contract."""


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
EVENT_KINDS = frozenset({"evidence", "observation", "catalyst", "counterargument"})
# "unreviewed" is the pass-through gate's stamp (ADR-0008): every event the
# pipeline drafts carries it. "proposed" survives only for the manual
# draft-event fallback's not-yet-filled-in skeleton.
REVIEW_STATUSES = frozenset({"proposed", "unreviewed", "keep_unlinked", "discarded"})
UNCERTAINTY_LEVELS = frozenset({"low", "medium", "high"})
REQUIRED_FIELDS = frozenset(
    {
        "event_id",
        "source",
        "source_locator",
        "date",
        "kind",
        "summary",
        "review_status",
        "uncertainty",
        "cited_span",
        "drafted_by",
        "run_id",
    }
)
OPTIONAL_FIELDS = frozenset(
    {"claims", "mechanisms", "counterarguments", "candidate_threads"}
)
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


@dataclass(frozen=True)
class CandidateEvent:
    """A machine-authored neutral observation, pass-through reviewed (ADR-0008)."""

    event_id: str
    source: str
    source_locator: str
    date: date
    kind: str
    summary: str
    review_status: str
    uncertainty: str
    cited_span: str
    drafted_by: str
    run_id: str
    claims: tuple[str, ...] = ()
    mechanisms: tuple[str, ...] = ()
    counterarguments: tuple[str, ...] = ()
    candidate_threads: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, record: dict[str, Any]) -> "CandidateEvent":
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            raise EventValidationError(f"missing required field(s): {', '.join(missing)}")
        unknown = sorted(record.keys() - ALLOWED_FIELDS)
        if unknown:
            raise EventValidationError(f"unknown field(s): {', '.join(unknown)}")

        event_id = _identifier(record["event_id"], "event_id")
        source = _identifier(record["source"], "source")
        source_locator = _non_empty_string(record["source_locator"], "source_locator")
        summary = _non_empty_string(record["summary"], "summary")
        if len(summary) > 600:
            raise EventValidationError("summary must be at most 600 characters")
        cited_span = _non_empty_string(record["cited_span"], "cited_span")
        if len(cited_span) > 600:
            raise EventValidationError("cited_span must be at most 600 characters")

        kind = _choice(record["kind"], "kind", EVENT_KINDS)
        review_status = _choice(record["review_status"], "review_status", REVIEW_STATUSES)
        uncertainty = _choice(record["uncertainty"], "uncertainty", UNCERTAINTY_LEVELS)

        return cls(
            event_id=event_id,
            source=source,
            source_locator=source_locator,
            date=_date(record["date"]),
            kind=kind,
            summary=summary,
            review_status=review_status,
            uncertainty=uncertainty,
            cited_span=cited_span,
            drafted_by=_identifier(record["drafted_by"], "drafted_by"),
            run_id=_identifier(record["run_id"], "run_id"),
            claims=_string_list(record.get("claims", []), "claims"),
            mechanisms=_string_list(record.get("mechanisms", []), "mechanisms"),
            counterarguments=_string_list(
                record.get("counterarguments", []), "counterarguments"
            ),
            candidate_threads=_identifier_list(
                record.get("candidate_threads", []), "candidate_threads"
            ),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "source_locator": self.source_locator,
            "date": self.date.isoformat(),
            "kind": self.kind,
            "summary": self.summary,
            "review_status": self.review_status,
            "uncertainty": self.uncertainty,
            "cited_span": self.cited_span,
            "drafted_by": self.drafted_by,
            "run_id": self.run_id,
            "claims": list(self.claims),
            "mechanisms": list(self.mechanisms),
            "counterarguments": list(self.counterarguments),
            "candidate_threads": list(self.candidate_threads),
        }


def load_candidate_event(path: Path) -> CandidateEvent:
    """Load and validate one YAML candidate event without modifying it."""
    try:
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise EventValidationError(f"invalid YAML in {path}: {error}") from error
    if not isinstance(record, dict):
        raise EventValidationError("event record must be a YAML mapping")
    return CandidateEvent.from_mapping(record)


def _identifier(value: Any, field: str) -> str:
    text = _non_empty_string(value, field)
    if not IDENTIFIER.fullmatch(text):
        raise EventValidationError(
            f"{field} must use lowercase letters, digits, and underscores, starting with a letter"
        )
    return text


def _identifier_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise EventValidationError(f"{field} must be a list")
    return tuple(_identifier(item, field) for item in value)


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise EventValidationError(f"{field} must be a list")
    return tuple(_non_empty_string(item, field) for item in value)


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EventValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _choice(value: Any, field: str, choices: frozenset[str]) -> str:
    text = _non_empty_string(value, field)
    if text not in choices:
        allowed = ", ".join(sorted(choices))
        raise EventValidationError(f"{field} must be one of: {allowed}")
    return text


def _date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise EventValidationError("date must be an ISO-8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise EventValidationError("date must be an ISO-8601 date") from error
