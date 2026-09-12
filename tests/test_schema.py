from __future__ import annotations

from datetime import date

import pytest

from signalweave.schema import CandidateEvent, EventValidationError


def valid_record() -> dict[str, object]:
    return {
        "event_id": "evt_2026_001",
        "source": "source_a",
        "source_locator": "doc_2026_001#segment_12",
        "date": "2026-09-11",
        "kind": "evidence",
        "summary": "A synthetic supplier constraint may shift bargaining power upstream.",
        "review_status": "unreviewed",
        "uncertainty": "medium",
        "cited_span": "A synthetic supplier constraint quote.",
        "drafted_by": "model_claude",
        "run_id": "run_abc123",
        "claims": ["A supply constraint may be emerging."],
        "mechanisms": ["Lower capacity can increase supplier leverage."],
        "counterarguments": ["Demand may normalize before pricing changes."],
        "candidate_threads": ["thread_supply_constraint"],
    }


def test_candidate_event_parses_a_valid_synthetic_record() -> None:
    event = CandidateEvent.from_mapping(valid_record())

    assert event.date == date(2026, 9, 11)
    assert event.candidate_threads == ("thread_supply_constraint",)


@pytest.mark.parametrize("field", ["event_id", "source_locator", "uncertainty"])
def test_candidate_event_requires_core_fields(field: str) -> None:
    record = valid_record()
    del record[field]

    with pytest.raises(EventValidationError, match=field):
        CandidateEvent.from_mapping(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("date", "2026/09/11", "ISO-8601"),
        ("kind", "verdict", "kind must be one of"),
        ("review_status", "accepted", "review_status must be one of"),
        ("uncertainty", "certain", "uncertainty must be one of"),
    ],
)
def test_candidate_event_rejects_invalid_controlled_values(
    field: str, value: str, message: str
) -> None:
    record = valid_record()
    record[field] = value

    with pytest.raises(EventValidationError, match=message):
        CandidateEvent.from_mapping(record)


def test_candidate_event_rejects_non_identifier_thread_links() -> None:
    record = valid_record()
    record["candidate_threads"] = ["Thread Supply Constraint"]

    with pytest.raises(EventValidationError, match="candidate_threads"):
        CandidateEvent.from_mapping(record)


def test_candidate_event_rejects_uncontracted_fields() -> None:
    record = valid_record()
    record["raw_text"] = "This field must never reach a candidate event card."

    with pytest.raises(EventValidationError, match="unknown field"):
        CandidateEvent.from_mapping(record)
