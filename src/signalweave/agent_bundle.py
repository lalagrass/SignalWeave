"""Deterministically import one interactive-agent transcript bundle.

This module deliberately has no provider SDK dependency.  An interactive agent
may have already processed a private transcript elsewhere; this importer only
validates its structured bundle against the local transcript, then writes the
same private records used by every other SignalWeave ingestion path.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from signalweave.basket import Basket, create_basket, write_basket
from signalweave.extract import TranscriptSegment, segment_transcript, write_candidate_draft
from signalweave.runs import Run, create_run, write_run
from signalweave.schema import CandidateEvent, EventValidationError, IDENTIFIER
from signalweave.threads import ResearchThread, create_thread, write_thread


SCHEMA_VERSION = 1
METHOD_VERSION = "agent_bundle_v1"
ROOT_FIELDS = frozenset({"schema_version", "provenance", "events", "story", "basket"})
PROVENANCE_FIELDS = frozenset(
    {"provider", "model_id", "model_locality", "drafted_by", "method_version", "created_at"}
)
EVENT_GROUP_FIELDS = frozenset({"segment", "proposals"})
EVENT_FIELDS = frozenset(
    {
        "event_id",
        "kind",
        "summary",
        "uncertainty",
        "cited_span",
        "claims",
        "mechanisms",
        "counterarguments",
        "candidate_threads",
    }
)
STORY_FIELDS = frozenset(
    {
        "thread_id",
        "mechanism",
        "open_question",
        "invalidation_conditions",
        "groups",
        "market_sentiment",
        "review_date",
    }
)
BASKET_FIELDS = frozenset({"instruments"})


class AgentBundleError(ValueError):
    """Raised when an interactive-agent bundle cannot safely be imported."""


@dataclass(frozen=True)
class BundleProvenance:
    provider: str
    model_id: str
    model_locality: str
    drafted_by: str
    created_at: datetime


@dataclass(frozen=True)
class EventGroup:
    segment: int
    proposals: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class AgentBundle:
    provenance: BundleProvenance
    events: tuple[EventGroup, ...]
    story: dict[str, Any]
    basket: dict[str, Any]
    canonical_json: str


@dataclass(frozen=True)
class AgentBundleImportResult:
    run_path: Path
    event_paths: tuple[Path, ...]
    thread_path: Path
    basket_path: Path


def load_agent_bundle(path: Path) -> AgentBundle:
    """Load one strict, canonical JSON ``agent-bundle-v1`` file.

    Error messages deliberately avoid echoing bundle values, which may be
    source-derived private material.
    """
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentBundleError("agent bundle must be valid JSON") from error
    if not isinstance(record, dict):
        raise AgentBundleError("agent bundle must be a JSON object")
    _exact_fields(record, ROOT_FIELDS, "agent bundle")
    if type(record["schema_version"]) is not int or record["schema_version"] != SCHEMA_VERSION:
        raise AgentBundleError("agent bundle must use schema_version 1")

    provenance = _provenance(record["provenance"])
    events = _events(record["events"])
    story = _object_with_fields(record["story"], STORY_FIELDS, "story")
    basket = _object_with_fields(record["basket"], BASKET_FIELDS, "basket")

    return AgentBundle(
        provenance=provenance,
        events=events,
        story=story,
        basket=basket,
        canonical_json=json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


def import_agent_bundle(
    transcript_path: Path,
    bundle_path: Path,
    *,
    source: str,
    document_id: str,
    event_date: str,
    workspace_root: Path,
) -> AgentBundleImportResult:
    """Validate a complete bundle before writing any private records.

    No network operation or provider client is used here.  The one private run
    records the finalized bundle and is deliberately shared by all records it
    imports: the interactive agent supplied one combined output, not invented
    per-step provenance.
    """
    inbox_events_directory, threads_directory, runs_directory = _private_directories(workspace_root)
    bundle = load_agent_bundle(bundle_path)
    try:
        date.fromisoformat(event_date)
        transcript = transcript_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise AgentBundleError("could not read and segment the private transcript") from error
    try:
        segments = segment_transcript(transcript, source=source, document_id=document_id)
    except EventValidationError as error:
        raise AgentBundleError("source and document identifiers must be valid") from error

    run = create_run(
        provider=bundle.provenance.provider,
        model_id=bundle.provenance.model_id,
        model_locality=bundle.provenance.model_locality,
        method_version=METHOD_VERSION,
        input_id=document_id,
        output=bundle.canonical_json,
        created_at=bundle.provenance.created_at,
    )
    candidates = _candidates(bundle, segments, source, event_date, run.run_id)
    thread = _thread(bundle, run.run_id)
    basket = _basket(bundle, thread, run.run_id)
    with _workspace_import_lock(runs_directory):
        planned_paths = _planned_paths(
            candidates, run, thread, inbox_events_directory, threads_directory, runs_directory
        )
        _preflight(planned_paths)

        try:
            run_path = write_run(run, runs_directory)
            event_paths = []
            for candidate in candidates:
                path = write_candidate_draft(candidate.to_mapping(), inbox_events_directory)
                event_paths.append(path)
            thread_path = write_thread(thread, threads_directory)
            basket_path = write_basket(basket, threads_directory)
        except OSError as error:
            _remove_planned(
                planned_paths, inbox_events_directory, threads_directory, runs_directory, thread.thread_id
            )
            raise AgentBundleError(
                "agent bundle import could not complete; no records were retained"
            ) from error

    return AgentBundleImportResult(
        run_path=run_path,
        event_paths=tuple(event_paths),
        thread_path=thread_path,
        basket_path=basket_path,
    )


def _provenance(value: Any) -> BundleProvenance:
    record = _object_with_fields(value, PROVENANCE_FIELDS, "bundle provenance")
    if record["method_version"] != METHOD_VERSION:
        raise AgentBundleError("bundle provenance must use method_version agent_bundle_v1")
    if not isinstance(record["provider"], str) or not IDENTIFIER.fullmatch(record["provider"]):
        raise AgentBundleError("bundle provider must be a neutral identifier")
    if not isinstance(record["model_id"], str) or not record["model_id"].strip():
        raise AgentBundleError("bundle model_id must be a non-empty string")
    if record["model_locality"] not in {"local", "remote"}:
        raise AgentBundleError("bundle model_locality must be local or remote")
    if not isinstance(record["drafted_by"], str) or not IDENTIFIER.fullmatch(record["drafted_by"]):
        raise AgentBundleError("bundle drafted_by must be a neutral identifier")
    if not isinstance(record["created_at"], str):
        raise AgentBundleError("bundle created_at must be an ISO-8601 timestamp")
    try:
        created_at = datetime.fromisoformat(record["created_at"])
    except ValueError as error:
        raise AgentBundleError("bundle created_at must be an ISO-8601 timestamp") from error
    if created_at.tzinfo is None:
        raise AgentBundleError("bundle created_at must include a timezone")
    return BundleProvenance(
        provider=record["provider"],
        model_id=record["model_id"].strip(),
        model_locality=record["model_locality"],
        drafted_by=record["drafted_by"],
        created_at=created_at,
    )


def _events(value: Any) -> tuple[EventGroup, ...]:
    if not isinstance(value, list) or not value:
        raise AgentBundleError("agent bundle events must be a non-empty list")
    groups: list[EventGroup] = []
    positions: set[int] = set()
    for item in value:
        record = _object_with_fields(item, EVENT_GROUP_FIELDS, "event group")
        position = record["segment"]
        if type(position) is not int or position < 1 or position in positions:
            raise AgentBundleError("each event group must name one unique positive segment")
        proposals = record["proposals"]
        if not isinstance(proposals, list) or not proposals:
            raise AgentBundleError("each event group must have a non-empty proposals list")
        normalized = tuple(_object_with_fields(proposal, EVENT_FIELDS, "event proposal") for proposal in proposals)
        groups.append(EventGroup(segment=position, proposals=normalized))
        positions.add(position)
    return tuple(groups)


def _candidates(
    bundle: AgentBundle,
    segments: tuple[TranscriptSegment, ...],
    source: str,
    event_date: str,
    run_id: str,
) -> tuple[CandidateEvent, ...]:
    segment_by_position = {segment.position: segment for segment in segments}
    candidates: list[CandidateEvent] = []
    event_ids: set[str] = set()
    for group in bundle.events:
        segment = segment_by_position.get(group.segment)
        if segment is None:
            raise AgentBundleError("bundle names a segment that is unavailable in the transcript")
        for proposal in group.proposals:
            record = {
                **proposal,
                "source": source,
                "source_locator": segment.source_locator,
                "date": event_date,
                "review_status": "unreviewed",
                "drafted_by": bundle.provenance.drafted_by,
                "run_id": run_id,
            }
            try:
                candidate = CandidateEvent.from_mapping(record)
            except EventValidationError as error:
                raise AgentBundleError("agent bundle contains an invalid event proposal") from error
            if candidate.event_id in event_ids:
                raise AgentBundleError("agent bundle event ids must be unique")
            if candidate.cited_span not in segment.text:
                raise AgentBundleError("a cited span does not exist in its declared transcript segment")
            candidates.append(candidate)
            event_ids.add(candidate.event_id)
    return tuple(candidates)


def _thread(bundle: AgentBundle, run_id: str) -> ResearchThread:
    try:
        return create_thread(
            **bundle.story,
            created_by=bundle.provenance.drafted_by,
            drafted_by=bundle.provenance.drafted_by,
            run_id=run_id,
            created_at=bundle.provenance.created_at,
        )
    except (TypeError, ValueError) as error:
        raise AgentBundleError("agent bundle contains an invalid story") from error


def _basket(bundle: AgentBundle, thread: ResearchThread, run_id: str) -> Basket:
    try:
        return create_basket(
            thread_id=thread.thread_id,
            instruments=bundle.basket["instruments"],
            drafted_by=bundle.provenance.drafted_by,
            run_id=run_id,
            created_at=bundle.provenance.created_at,
        )
    except (TypeError, ValueError) as error:
        raise AgentBundleError("agent bundle contains an invalid basket") from error


def _private_directories(workspace_root: Path) -> tuple[Path, Path, Path]:
    """Derive legal destinations from the verified Git top-level only."""
    root = workspace_root.resolve()
    try:
        result = subprocess.run(
            ("git", "-C", str(root), "rev-parse", "--show-toplevel"),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise AgentBundleError("agent bundle import requires a Git workspace root") from error
    if result.returncode != 0 or not result.stdout.strip() or Path(result.stdout.strip()).resolve() != root:
        raise AgentBundleError("agent bundle import requires the Git workspace top-level")
    directories = (
        root / "data" / "inbox" / "events",
        root / "data" / "private" / "threads",
        root / "data" / "private" / "runs",
    )
    for directory in directories:
        resolved = directory.resolve()
        if resolved != directory:
            raise AgentBundleError("agent bundle outputs must use exact private workspace roots")
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise AgentBundleError("agent bundle outputs must remain inside the workspace private zones") from error
        relative_probe = resolved.relative_to(root) / ".agent_bundle_probe"
        ignored = subprocess.run(
            ("git", "-C", str(root), "check-ignore", "-q", "--no-index", str(relative_probe)),
            check=False,
            capture_output=True,
            text=True,
        )
        if ignored.returncode != 0:
            raise AgentBundleError("agent bundle outputs must use Git-ignored private zones")
    return directories


@contextmanager
def _workspace_import_lock(runs_directory: Path):
    """Serialize imports so rollback cannot remove another import's records."""
    runs_directory.mkdir(parents=True, exist_ok=True)
    lock_path = runs_directory / ".agent_bundle_import.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise AgentBundleError("another agent bundle import is already in progress") from error
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _planned_paths(
    candidates: tuple[CandidateEvent, ...],
    run: Run,
    thread: ResearchThread,
    inbox_events_directory: Path,
    threads_directory: Path,
    runs_directory: Path,
) -> tuple[Path, ...]:
    return (
        runs_directory / f"{run.run_id}.yaml",
        threads_directory / thread.thread_id,
        threads_directory / thread.thread_id / "thread.yaml",
        *(inbox_events_directory / f"{candidate.event_id}.yaml" for candidate in candidates),
        threads_directory / thread.thread_id / "basket.yaml",
    )


def _preflight(planned_paths: tuple[Path, ...]) -> None:
    if any(path.exists() for path in planned_paths):
        raise AgentBundleError("agent bundle import collides with existing private records")


def _remove_planned(
    planned_paths: tuple[Path, ...],
    inbox_events_directory: Path,
    threads_directory: Path,
    runs_directory: Path,
    thread_id: str,
) -> None:
    for path in reversed(planned_paths):
        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
        except OSError:
            pass
    for directory in (threads_directory / thread_id, inbox_events_directory, runs_directory):
        try:
            directory.rmdir()
        except OSError:
            pass


def _object_with_fields(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AgentBundleError(f"{label} must be a JSON object")
    _exact_fields(value, fields, label)
    return dict(value)


def _exact_fields(record: dict[str, Any], fields: frozenset[str], label: str) -> None:
    if record.keys() != fields:
        raise AgentBundleError(f"{label} has invalid fields")
