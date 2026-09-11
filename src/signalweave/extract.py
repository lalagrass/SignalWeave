"""Private transcript segmentation and model-independent candidate extraction."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Protocol

import yaml

from signalweave.schema import CandidateEvent, EventValidationError, IDENTIFIER


MINIMUM_SEGMENT_LENGTH = 24
PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")


@dataclass(frozen=True)
class TranscriptSegment:
    """A private, in-memory source segment that must not be persisted by this module."""

    source: str
    source_locator: str
    position: int
    text: str


class CandidateProposer(Protocol):
    """Return unreviewed candidate mappings for one private source segment."""

    def propose(self, segment: TranscriptSegment) -> Iterable[Mapping[str, Any]]: ...


class NoopCandidateProposer:
    """Safe default before an AI or other proposal mechanism is configured."""

    def propose(self, segment: TranscriptSegment) -> Iterable[Mapping[str, Any]]:
        return ()


def segment_transcript(
    text: str,
    *,
    source: str,
    document_id: str,
    minimum_length: int = MINIMUM_SEGMENT_LENGTH,
) -> tuple[TranscriptSegment, ...]:
    """Split private text into stable, in-memory paragraph segments.

    Segment content is returned only to the caller. This function does not write
    text, logs, or derived output to disk.
    """
    _validate_identifier(source, "source")
    _validate_identifier(document_id, "document_id")
    if minimum_length < 1:
        raise EventValidationError("minimum_length must be at least 1")

    segments: list[TranscriptSegment] = []
    for paragraph in PARAGRAPH_BREAK.split(text):
        cleaned = paragraph.strip()
        if len(cleaned) < minimum_length:
            continue
        position = len(segments) + 1
        segments.append(
            TranscriptSegment(
                source=source,
                source_locator=f"{document_id}#segment_{position}",
                position=position,
                text=cleaned,
            )
        )
    return tuple(segments)


def extract_candidates(
    segments: Iterable[TranscriptSegment], proposer: CandidateProposer
) -> tuple[CandidateEvent, ...]:
    """Validate candidate proposals while enforcing source and review boundaries."""
    candidates: list[CandidateEvent] = []
    for segment in segments:
        for proposal in proposer.propose(segment):
            record = dict(proposal)
            record["source"] = segment.source
            record["source_locator"] = segment.source_locator
            record["review_status"] = "proposed"
            candidates.append(CandidateEvent.from_mapping(record))
    return tuple(candidates)


def select_segment(segments: tuple[TranscriptSegment, ...], position: int) -> TranscriptSegment:
    """Return the segment at a 1-indexed position without exposing any text."""
    if not segments:
        raise EventValidationError("no segments are available to draft from")
    if not (1 <= position <= len(segments)):
        raise EventValidationError(f"segment position must be between 1 and {len(segments)}")
    return segments[position - 1]


def draft_candidate_event(
    segment: TranscriptSegment, *, event_id: str, event_date: str
) -> dict[str, Any]:
    """Build a candidate skeleton that carries only machine-known fields.

    The human-owned fields are emitted empty so `validate-event` fails until a
    reviewer fills them in; no segment text is ever placed in the result.
    """
    _validate_identifier(event_id, "event_id")
    return {
        "event_id": event_id,
        "source": segment.source,
        "source_locator": segment.source_locator,
        "date": event_date,
        "kind": "",
        "summary": "",
        "uncertainty": "",
        "review_status": "proposed",
        "claims": [],
        "mechanisms": [],
        "counterarguments": [],
        "candidate_threads": [],
    }


def write_candidate_draft(record: Mapping[str, Any], inbox_directory: Path) -> Path:
    """Write a candidate draft skeleton without overwriting an existing card."""
    inbox_directory.mkdir(parents=True, exist_ok=True)
    path = inbox_directory / f"{record['event_id']}.yaml"
    if path.exists():
        raise FileExistsError(f"candidate event already exists: {path}")
    path.write_text(
        yaml.safe_dump(dict(record), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _validate_identifier(value: str, field: str) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise EventValidationError(
            f"{field} must use lowercase letters, digits, and underscores, starting with a letter"
        )
