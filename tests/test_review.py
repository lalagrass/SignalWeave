from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from signalweave.review import ReviewValidationError, create_review, write_review
from signalweave.schema import CandidateEvent


def candidate_event() -> CandidateEvent:
    return CandidateEvent.from_mapping(
        {
            "event_id": "evt_2026_001",
            "source": "source_a",
            "source_locator": "doc_2026_001#segment_12",
            "date": "2026-09-11",
            "kind": "evidence",
            "summary": "A synthetic observation.",
            "review_status": "unreviewed",
            "uncertainty": "medium",
            "cited_span": "A synthetic quoted span.",
            "drafted_by": "model_synthetic",
            "run_id": "run_synthetic001",
        }
    )


@pytest.mark.parametrize("action", ["keep_unlinked", "discard"])
def test_review_actions_without_thread(action: str) -> None:
    record = create_review(
        candidate_event(),
        review_id="review_2026_001",
        action=action,
        reviewer="researcher_a",
        reviewed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )

    assert record.action == action
    assert record.suggested_thread is None


def test_link_review_requires_and_retains_a_suggested_thread() -> None:
    record = create_review(
        candidate_event(),
        review_id="review_2026_001",
        action="link_to_thread",
        reviewer="researcher_a",
        suggested_thread="thread_supply_constraint",
        reviewed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )

    assert record.suggested_thread == "thread_supply_constraint"


@pytest.mark.parametrize(
    ("action", "suggested_thread", "message"),
    [
        ("link_to_thread", None, "suggested_thread"),
        ("discard", "thread_supply_constraint", "only allowed"),
    ],
)
def test_review_rejects_invalid_thread_combinations(
    action: str, suggested_thread: str | None, message: str
) -> None:
    with pytest.raises(ReviewValidationError, match=message):
        create_review(
            candidate_event(),
            review_id="review_2026_001",
            action=action,
            reviewer="researcher_a",
            suggested_thread=suggested_thread,
        )


def test_write_review_appends_without_overwriting(tmp_path: Path) -> None:
    record = create_review(
        candidate_event(),
        review_id="review_2026_001",
        action="keep_unlinked",
        reviewer="researcher_a",
        reviewed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )

    path = write_review(record, tmp_path / "data" / "inbox" / "reviews")

    assert yaml.safe_load(path.read_text(encoding="utf-8"))["event_id"] == "evt_2026_001"
    with pytest.raises(FileExistsError, match="already exists"):
        write_review(record, tmp_path / "data" / "inbox" / "reviews")
