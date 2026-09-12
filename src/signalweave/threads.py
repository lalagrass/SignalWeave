"""Human-owned, append-only private research threads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from signalweave.review import ReviewRecord
from signalweave.schema import IDENTIFIER


EVIDENCE_ROLES = frozenset({"supporting", "counter"})
# Pass-through gate (ADR-0008): a story is never anything but unreviewed.
THREAD_REVIEW_STATUSES = frozenset({"unreviewed"})
THREAD_REQUIRED_FIELDS = frozenset(
    {
        "thread_id",
        "mechanism",
        "open_question",
        "invalidation_conditions",
        "groups",
        "market_sentiment",
        "review_date",
        "created_at",
        "created_by",
        "drafted_by",
        "review_status",
        "run_id",
    }
)
UPDATE_REQUIRED_FIELDS = frozenset(
    {
        "update_id",
        "thread_id",
        "event_id",
        "review_id",
        "evidence_role",
        "summary",
        "date",
        "added_at",
        "added_by",
        "drafted_by",
    }
)


class ThreadValidationError(ValueError):
    """Raised when a research thread or update violates its contract."""


@dataclass(frozen=True)
class ResearchThread:
    """A story: a hypothesis about a mechanism (PRODUCT.md; "thread" in code,
    "story" in the milestone 2 docs — the same record under two names).

    `created_by` is the human or model that accepts and owns the record.
    `drafted_by` is whoever produced its free text (mechanism, open question,
    groups, market sentiment, invalidation conditions) — a human id, or a
    model/agent identifier when a human has not composed that text
    themselves. The two are tracked separately so a thread can never look
    human-authored by default. Under the pass-through gate (ADR-0008),
    `review_status` is always `unreviewed` and `run_id` names the pipeline run
    that drafted it.
    """

    thread_id: str
    mechanism: str
    open_question: str
    invalidation_conditions: tuple[str, ...]
    groups: tuple[str, ...]
    market_sentiment: str
    review_date: date
    created_at: datetime
    created_by: str
    drafted_by: str
    review_status: str
    run_id: str

    @classmethod
    def from_mapping(cls, record: dict[str, Any]) -> "ResearchThread":
        _require_exact_fields(record, THREAD_REQUIRED_FIELDS, "thread")
        conditions = _string_list(record["invalidation_conditions"], "invalidation_conditions")
        if not conditions:
            raise ThreadValidationError("invalidation_conditions must not be empty")
        groups = _string_list(record["groups"], "groups")
        if not groups:
            raise ThreadValidationError("groups must not be empty")
        review_status = _non_empty_string(record["review_status"], "review_status")
        if review_status not in THREAD_REVIEW_STATUSES:
            raise ThreadValidationError("review_status must be 'unreviewed'")
        return cls(
            thread_id=_identifier(record["thread_id"], "thread_id"),
            mechanism=_summary(record["mechanism"], "mechanism"),
            open_question=_summary(record["open_question"], "open_question"),
            invalidation_conditions=conditions,
            groups=groups,
            market_sentiment=_summary(record["market_sentiment"], "market_sentiment"),
            review_date=_date(record["review_date"], "review_date"),
            created_at=_datetime(record["created_at"], "created_at"),
            created_by=_identifier(record["created_by"], "created_by"),
            drafted_by=_identifier(record["drafted_by"], "drafted_by"),
            review_status=review_status,
            run_id=_identifier(record["run_id"], "run_id"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "mechanism": self.mechanism,
            "open_question": self.open_question,
            "invalidation_conditions": list(self.invalidation_conditions),
            "groups": list(self.groups),
            "market_sentiment": self.market_sentiment,
            "review_date": self.review_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "drafted_by": self.drafted_by,
            "review_status": self.review_status,
            "run_id": self.run_id,
        }


@dataclass(frozen=True)
class ThreadUpdate:
    """A dated supporting or counter update linked to a review decision.

    `added_by` is the human who accepts and owns the update. `drafted_by` is
    whoever wrote its free-text `summary` — a human id, or an agent
    identifier when a human has not yet composed that text themselves.
    """

    update_id: str
    thread_id: str
    event_id: str
    review_id: str
    evidence_role: str
    summary: str
    date: date
    added_at: datetime
    added_by: str
    drafted_by: str

    @classmethod
    def from_mapping(cls, record: dict[str, Any]) -> "ThreadUpdate":
        _require_exact_fields(record, UPDATE_REQUIRED_FIELDS, "thread update")
        evidence_role = _non_empty_string(record["evidence_role"], "evidence_role")
        if evidence_role not in EVIDENCE_ROLES:
            raise ThreadValidationError(
                f"evidence_role must be one of: {', '.join(sorted(EVIDENCE_ROLES))}"
            )
        return cls(
            update_id=_identifier(record["update_id"], "update_id"),
            thread_id=_identifier(record["thread_id"], "thread_id"),
            event_id=_identifier(record["event_id"], "event_id"),
            review_id=_identifier(record["review_id"], "review_id"),
            evidence_role=evidence_role,
            summary=_summary(record["summary"], "summary"),
            date=_date(record["date"], "date"),
            added_at=_datetime(record["added_at"], "added_at"),
            added_by=_identifier(record["added_by"], "added_by"),
            drafted_by=_identifier(record["drafted_by"], "drafted_by"),
        )

    def to_mapping(self) -> dict[str, str]:
        return {
            "update_id": self.update_id,
            "thread_id": self.thread_id,
            "event_id": self.event_id,
            "review_id": self.review_id,
            "evidence_role": self.evidence_role,
            "summary": self.summary,
            "date": self.date.isoformat(),
            "added_at": self.added_at.isoformat(),
            "added_by": self.added_by,
            "drafted_by": self.drafted_by,
        }


def create_thread(
    *,
    thread_id: str,
    mechanism: str,
    open_question: str,
    invalidation_conditions: list[str],
    groups: list[str],
    market_sentiment: str,
    review_date: str,
    created_by: str,
    drafted_by: str,
    run_id: str,
    created_at: datetime | None = None,
) -> ResearchThread:
    """Create a story record. `review_status` is always `unreviewed`
    (ADR-0008) — it is not a parameter, because nothing legitimately sets it
    to anything else today.

    `created_by` and `drafted_by` may be the same id when a human wrote and
    accepts the record themselves, or when a pipeline run owns and drafted it
    end to end; they must be supplied separately so an agent-drafted record
    cannot default to looking human-authored.
    """
    return ResearchThread.from_mapping(
        {
            "thread_id": thread_id,
            "mechanism": mechanism,
            "open_question": open_question,
            "invalidation_conditions": invalidation_conditions,
            "groups": groups,
            "market_sentiment": market_sentiment,
            "review_date": review_date,
            "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
            "created_by": created_by,
            "drafted_by": drafted_by,
            "review_status": "unreviewed",
            "run_id": run_id,
        }
    )


def create_thread_update(
    *,
    thread_id: str,
    event_id: str,
    review: ReviewRecord,
    update_id: str,
    evidence_role: str,
    summary: str,
    event_date: str,
    added_by: str,
    drafted_by: str,
    added_at: datetime | None = None,
) -> ThreadUpdate:
    """Create an update only when the review explicitly links the target thread.

    `added_by` and `drafted_by` may be the same id when a human wrote and
    accepts the update themselves; they must be supplied separately so an
    agent-drafted summary cannot default to looking human-authored.
    """
    if review.action != "link_to_thread" or review.suggested_thread != thread_id:
        raise ThreadValidationError(
            "review must use link_to_thread and suggest the target thread"
        )
    if review.event_id != event_id:
        raise ThreadValidationError("review event_id must match the thread update event_id")
    return ThreadUpdate.from_mapping(
        {
            "update_id": update_id,
            "thread_id": thread_id,
            "event_id": event_id,
            "review_id": review.review_id,
            "evidence_role": evidence_role,
            "summary": summary,
            "date": event_date,
            "added_at": (added_at or datetime.now(timezone.utc)).isoformat(),
            "added_by": added_by,
            "drafted_by": drafted_by,
        }
    )


def write_thread(thread: ResearchThread, threads_directory: Path) -> Path:
    """Create a private thread directory without overwriting an existing thread."""
    thread_directory = threads_directory / thread.thread_id
    if thread_directory.exists():
        raise FileExistsError(f"thread already exists: {thread_directory}")
    thread_directory.mkdir(parents=True)
    path = thread_directory / "thread.yaml"
    path.write_text(
        yaml.safe_dump(thread.to_mapping(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def append_thread_update(update: ThreadUpdate, threads_directory: Path) -> Path:
    """Append one private evidence update without altering earlier thread files."""
    thread_directory = threads_directory / update.thread_id
    if not (thread_directory / "thread.yaml").is_file():
        raise FileNotFoundError(f"thread does not exist: {update.thread_id}")
    updates_directory = thread_directory / "updates"
    updates_directory.mkdir(exist_ok=True)
    path = updates_directory / f"{update.update_id}.yaml"
    if path.exists():
        raise FileExistsError(f"thread update already exists: {path}")
    path.write_text(
        yaml.safe_dump(update.to_mapping(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def list_thread_ids(threads_directory: Path) -> tuple[str, ...]:
    """Return the ids of every private thread, sorted for deterministic output."""
    if not threads_directory.is_dir():
        return ()
    return tuple(
        sorted(
            entry.name
            for entry in threads_directory.iterdir()
            if entry.is_dir() and (entry / "thread.yaml").is_file()
        )
    )


def load_thread(thread_directory: Path) -> ResearchThread:
    """Load one private thread header without changing it."""
    path = thread_directory / "thread.yaml"
    try:
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ThreadValidationError(f"invalid YAML in {path}: {error}") from error
    if not isinstance(record, dict):
        raise ThreadValidationError("thread record must be a YAML mapping")
    return ResearchThread.from_mapping(record)


def load_thread_updates(thread_directory: Path) -> tuple[ThreadUpdate, ...]:
    """Load every update for one thread, ordered by date then update_id."""
    updates_directory = thread_directory / "updates"
    if not updates_directory.is_dir():
        return ()
    updates: list[ThreadUpdate] = []
    for path in sorted(updates_directory.glob("*.yaml")):
        try:
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ThreadValidationError(f"invalid YAML in {path}: {error}") from error
        if not isinstance(record, dict):
            raise ThreadValidationError(f"thread update record must be a YAML mapping: {path}")
        updates.append(ThreadUpdate.from_mapping(record))
    return tuple(sorted(updates, key=lambda update: (update.date, update.update_id)))


def _require_exact_fields(record: dict[str, Any], required: frozenset[str], label: str) -> None:
    missing = sorted(required - record.keys())
    if missing:
        raise ThreadValidationError(f"missing required {label} field(s): {', '.join(missing)}")
    unknown = sorted(record.keys() - required)
    if unknown:
        raise ThreadValidationError(f"unknown {label} field(s): {', '.join(unknown)}")


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ThreadValidationError(
            f"{field} must use lowercase letters, digits, and underscores, starting with a letter"
        )
    return value


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ThreadValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _summary(value: Any, field: str) -> str:
    text = _non_empty_string(value, field)
    if len(text) > 600:
        raise ThreadValidationError(f"{field} must be at most 600 characters")
    return text


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ThreadValidationError(f"{field} must be a list")
    return tuple(_summary(item, field) for item in value)


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ThreadValidationError(f"{field} must be an ISO-8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ThreadValidationError(f"{field} must be an ISO-8601 date") from error


def _datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ThreadValidationError(f"{field} must be an ISO-8601 timestamp")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise ThreadValidationError(f"{field} must be an ISO-8601 timestamp") from error
    if timestamp.tzinfo is None:
        raise ThreadValidationError(f"{field} must include a timezone")
    return timestamp
