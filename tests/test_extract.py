from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from signalweave.extract import (
    NoopCandidateProposer,
    TranscriptSegment,
    draft_candidate_event,
    extract_candidates,
    segment_transcript,
    select_segment,
    write_candidate_draft,
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


def test_select_segment_rejects_out_of_range_position_without_naming_text() -> None:
    segments = segment_transcript(
        "First synthetic paragraph is long enough to be a segment.\n\n"
        "Second synthetic paragraph is also long enough to be a segment.",
        source="source_a",
        document_id="doc_2026_001",
    )

    with pytest.raises(EventValidationError, match=r"between 1 and 2") as excinfo:
        select_segment(segments, 12)
    assert "synthetic" not in str(excinfo.value).lower()


def test_select_segment_rejects_position_when_no_segments_exist() -> None:
    with pytest.raises(EventValidationError, match="no segments are available"):
        select_segment((), 1)


def test_draft_candidate_event_carries_only_machine_known_fields() -> None:
    segment = TranscriptSegment(
        source="source_a",
        source_locator="doc_2026_001#segment_12",
        position=12,
        text="Synthetic private text that must never reach the draft.",
    )

    record = draft_candidate_event(segment, event_id="evt_2026_001", event_date="2026-09-11")

    assert record == {
        "event_id": "evt_2026_001",
        "source": "source_a",
        "source_locator": "doc_2026_001#segment_12",
        "date": "2026-09-11",
        "kind": "",
        "summary": "",
        "uncertainty": "",
        "review_status": "proposed",
        "claims": [],
        "mechanisms": [],
        "counterarguments": [],
        "candidate_threads": [],
    }
    assert "Synthetic private text" not in yaml.safe_dump(record)


def test_write_candidate_draft_refuses_to_overwrite(tmp_path: Path) -> None:
    record = {"event_id": "evt_2026_001", "source": "source_a"}
    inbox = tmp_path / "data" / "inbox" / "events"

    path = write_candidate_draft(record, inbox)

    assert path == inbox / "evt_2026_001.yaml"
    with pytest.raises(FileExistsError, match="already exists"):
        write_candidate_draft(record, inbox)
