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
    """Validate candidate proposals while enforcing source and review boundaries.

    `source`, `source_locator`, and `review_status` are overwritten regardless
    of what the proposer supplies, so a proposer can never place itself in a
    different source or self-stamp anything other than `unreviewed`
    (ADR-0008 — the pass-through gate, not a proposer's own claim, decides
    that). `drafted_by` and `run_id` are left as the proposer set them: only
    the proposer knows which model or run actually produced the text.

    The only content check performed here is mechanical (ADR-0008): the
    `cited_span` a proposal names must verifiably exist in the segment it was
    drawn from. A proposal that fails this check raises rather than being
    silently dropped, so the caller decides how to handle it per segment.
    """
    candidates: list[CandidateEvent] = []
    for segment in segments:
        for proposal in proposer.propose(segment):
            record = dict(proposal)
            record["source"] = segment.source
            record["source_locator"] = segment.source_locator
            record["review_status"] = "unreviewed"
            candidate = CandidateEvent.from_mapping(record)
            if candidate.cited_span not in segment.text:
                raise EventValidationError(
                    "cited_span does not verifiably exist in its source segment"
                )
            candidates.append(candidate)
    return tuple(candidates)


def select_segment(segments: tuple[TranscriptSegment, ...], position: int) -> TranscriptSegment:
    """Return the segment at a 1-indexed position without exposing any text."""
    if not segments:
        raise EventValidationError("no segments are available to draft from")
    if not (1 <= position <= len(segments)):
        raise EventValidationError(f"segment position must be between 1 and {len(segments)}")
    return segments[position - 1]


def draft_candidate_event(
    segment: TranscriptSegment, *, event_id: str, event_date: str, drafted_by: str
) -> dict[str, Any]:
    """Build a candidate skeleton that carries only machine-known fields.

    The human-owned fields — including `cited_span`, which this function never
    fills in — are emitted empty so `validate-event` fails until a reviewer
    finds the span themselves and pastes it in; no segment text is ever placed
    in the result. This is the manual fallback (ADR-0008): there is no pipeline
    run behind it, so `run_id` is fixed to the literal value `manual` rather
    than asking the human to invent one.
    """
    _validate_identifier(event_id, "event_id")
    _validate_identifier(drafted_by, "drafted_by")
    return {
        "event_id": event_id,
        "source": segment.source,
        "source_locator": segment.source_locator,
        "date": event_date,
        "kind": "",
        "summary": "",
        "uncertainty": "",
        "cited_span": "",
        "review_status": "proposed",
        "drafted_by": drafted_by,
        "run_id": "manual",
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
