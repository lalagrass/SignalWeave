"""Private transcript segmentation and model-independent candidate extraction."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import re
from typing import Any, Protocol

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


def _validate_identifier(value: str, field: str) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise EventValidationError(
            f"{field} must use lowercase letters, digits, and underscores, starting with a letter"
        )
