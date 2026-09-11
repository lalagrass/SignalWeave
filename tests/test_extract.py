from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pytest

from signalweave.extract import (
    NoopCandidateProposer,
    TranscriptSegment,
    extract_candidates,
    segment_transcript,
)
from signalweave.schema import EventValidationError


class SyntheticProposer:
    def propose(self, segment: TranscriptSegment) -> Iterable[Mapping[str, Any]]:
        return (
            {
                "event_id": f"evt_2026_{segment.position:03d}",
                "source": "wrong_source",
                "source_locator": "wrong_document#segment_99",
                "date": "2026-09-11",
                "kind": "observation",
                "summary": "A synthetic observation may warrant review.",
                "review_status": "accepted",
                "uncertainty": "medium",
            },
        )


def test_segment_transcript_creates_stable_locators_without_persisting_text() -> None:
    segments = segment_transcript(
        "Short.\n\nFirst synthetic paragraph is long enough to be a segment.\n\n"
        "Second synthetic paragraph is also long enough to be a segment.",
        source="source_a",
        document_id="doc_2026_001",
    )

    assert [segment.source_locator for segment in segments] == [
        "doc_2026_001#segment_1",
        "doc_2026_001#segment_2",
    ]


def test_segment_transcript_can_return_no_segments() -> None:
    assert segment_transcript("Too short.", source="source_a", document_id="doc_2026_001") == ()


def test_extraction_enforces_segment_locator_and_proposed_review_status() -> None:
    segment = TranscriptSegment(
        source="source_a",
        source_locator="doc_2026_001#segment_1",
        position=1,
        text="Synthetic private text that is never written by the extractor.",
    )

    candidate = extract_candidates((segment,), SyntheticProposer())[0]

    assert candidate.source == "source_a"
    assert candidate.source_locator == "doc_2026_001#segment_1"
    assert candidate.review_status == "proposed"


def test_extraction_rejects_invalid_proposer_output() -> None:
    class InvalidProposer:
        def propose(self, segment: TranscriptSegment) -> Iterable[Mapping[str, Any]]:
            return ({"event_id": "evt_2026_001"},)

    segment = TranscriptSegment("source_a", "doc_2026_001#segment_1", 1, "Synthetic text")

    with pytest.raises(EventValidationError, match="missing required field"):
        extract_candidates((segment,), InvalidProposer())


def test_noop_proposer_emits_no_candidates() -> None:
    segment = TranscriptSegment("source_a", "doc_2026_001#segment_1", 1, "Synthetic text")

    assert extract_candidates((segment,), NoopCandidateProposer()) == ()
