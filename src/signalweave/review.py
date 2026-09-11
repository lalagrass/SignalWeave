"""Private, append-only review decisions for candidate events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from signalweave.schema import CandidateEvent, EventValidationError, IDENTIFIER


REVIEW_ACTIONS = frozenset({"keep_unlinked", "discard", "link_to_thread"})
REQUIRED_FIELDS = frozenset(
    {"review_id", "event_id", "source_locator", "action", "reviewed_at", "reviewer"}
)
OPTIONAL_FIELDS = frozenset({"reason", "suggested_thread"})


class ReviewValidationError(ValueError):
    """Raised when a review decision violates the review contract."""


@dataclass(frozen=True)
class ReviewRecord:
    """One immutable reviewer decision about a candidate event."""

    review_id: str
    event_id: str
    source_locator: str
    action: str
    reviewed_at: datetime
    reviewer: str
    reason: str | None = None
    suggested_thread: str | None = None

    @classmethod
    def from_mapping(cls, record: dict[str, Any]) -> "ReviewRecord":
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            raise ReviewValidationError(f"missing required field(s): {', '.join(missing)}")
        unknown = sorted(record.keys() - (REQUIRED_FIELDS | OPTIONAL_FIELDS))
        if unknown:
            raise ReviewValidationError(f"unknown field(s): {', '.join(unknown)}")

        action = _action(record["action"])
        suggested_thread = record.get("suggested_thread")
        if action == "link_to_thread":
            suggested_thread = _identifier(suggested_thread, "suggested_thread")
        elif suggested_thread is not None:
            raise ReviewValidationError(
                "suggested_thread is only allowed when action is link_to_thread"
            )

        return cls(
            review_id=_identifier(record["review_id"], "review_id"),
            event_id=_identifier(record["event_id"], "event_id"),
            source_locator=_non_empty_string(record["source_locator"], "source_locator"),
            action=action,
            reviewed_at=_datetime(record["reviewed_at"]),
            reviewer=_identifier(record["reviewer"], "reviewer"),
            reason=_optional_string(record.get("reason"), "reason"),
            suggested_thread=suggested_thread,
        )

    def to_mapping(self) -> dict[str, str]:
        record = {
            "review_id": self.review_id,
            "event_id": self.event_id,
            "source_locator": self.source_locator,
            "action": self.action,
            "reviewed_at": self.reviewed_at.isoformat(),
            "reviewer": self.reviewer,
        }
        if self.reason is not None:
            record["reason"] = self.reason
        if self.suggested_thread is not None:
            record["suggested_thread"] = self.suggested_thread
        return record


def create_review(
    event: CandidateEvent,
    *,
    review_id: str,
    action: str,
    reviewer: str,
    reviewed_at: datetime | None = None,
    reason: str | None = None,
    suggested_thread: str | None = None,
) -> ReviewRecord:
    """Create a review without mutating the candidate event or any thread."""
    return ReviewRecord.from_mapping(
        {
            "review_id": review_id,
            "event_id": event.event_id,
            "source_locator": event.source_locator,
            "action": action,
            "reviewed_at": (reviewed_at or datetime.now(timezone.utc)).isoformat(),
            "reviewer": reviewer,
            **({"reason": reason} if reason is not None else {}),
            **({"suggested_thread": suggested_thread} if suggested_thread is not None else {}),
        }
    )


def write_review(record: ReviewRecord, reviews_directory: Path) -> Path:
    """Append a review record by creating a new private YAML file.

    The caller supplies a private directory. Existing records are never
    overwritten, so subsequent reviewer decisions remain auditable.
    """
    reviews_directory.mkdir(parents=True, exist_ok=True)
    path = reviews_directory / f"{record.review_id}.yaml"
    if path.exists():
        raise FileExistsError(f"review record already exists: {path}")
    path.write_text(
        yaml.safe_dump(record.to_mapping(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ReviewValidationError(
            f"{field} must use lowercase letters, digits, and underscores, starting with a letter"
        )
    return value


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _non_empty_string(value, field)


def _action(value: Any) -> str:
    action = _non_empty_string(value, "action")
    if action not in REVIEW_ACTIONS:
        raise ReviewValidationError(f"action must be one of: {', '.join(sorted(REVIEW_ACTIONS))}")
    return action


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ReviewValidationError("reviewed_at must be an ISO-8601 timestamp")
    try:
        reviewed_at = datetime.fromisoformat(value)
    except ValueError as error:
        raise ReviewValidationError("reviewed_at must be an ISO-8601 timestamp") from error
    if reviewed_at.tzinfo is None:
        raise ReviewValidationError("reviewed_at must include a timezone")
    return reviewed_at
