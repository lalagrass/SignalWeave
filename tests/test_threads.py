from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from signalweave.review import ReviewRecord
from signalweave.threads import (
    ThreadValidationError,
    append_thread_update,
    create_thread,
    create_thread_update,
    list_thread_ids,
    load_thread,
    load_thread_updates,
    write_thread,
)


def linked_review(*, thread_id: str = "thread_supply_constraint") -> ReviewRecord:
    return ReviewRecord.from_mapping(
        {
            "review_id": "review_2026_001",
            "event_id": "evt_2026_001",
            "source_locator": "doc_2026_001#segment_12",
            "action": "link_to_thread",
            "reviewed_at": "2026-09-11T00:00:00+00:00",
            "reviewer": "researcher_a",
            "suggested_thread": thread_id,
        }
    )


def thread() -> object:
    return create_thread(
        thread_id="thread_supply_constraint",
        mechanism="Synthetic capacity constraints can increase supplier leverage.",
        open_question="Will capacity remain constrained through the next review date?",
        invalidation_conditions=["Synthetic demand normalizes before pricing changes."],
        review_date="2026-12-15",
        created_by="researcher_a",
        drafted_by="researcher_a",
        created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )


def test_thread_requires_human_mechanism_question_invalidation_and_review_date() -> None:
    with pytest.raises(ThreadValidationError, match="invalidation_conditions must not be empty"):
        create_thread(
            thread_id="thread_supply_constraint",
            mechanism="A synthetic mechanism.",
            open_question="A synthetic question?",
            invalidation_conditions=[],
            review_date="2026-12-15",
            created_by="researcher_a",
            drafted_by="researcher_a",
        )


def test_thread_tracks_drafted_by_separately_from_created_by() -> None:
    record = create_thread(
        thread_id="thread_supply_constraint",
        mechanism="A synthetic mechanism.",
        open_question="A synthetic question?",
        invalidation_conditions=["A synthetic invalidation condition."],
        review_date="2026-12-15",
        created_by="researcher_a",
        drafted_by="agent_signalweave",
        created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )

    assert record.created_by == "researcher_a"
    assert record.drafted_by == "agent_signalweave"


@pytest.mark.parametrize("evidence_role", ["supporting", "counter"])
def test_thread_update_accepts_supporting_and_counter_evidence(evidence_role: str) -> None:
    update = create_thread_update(
        thread_id="thread_supply_constraint",
        event_id="evt_2026_001",
        review=linked_review(),
        update_id="update_2026_001",
        evidence_role=evidence_role,
        summary="A synthetic reviewed observation is relevant to the hypothesis.",
        event_date="2026-09-11",
        added_by="researcher_a",
        drafted_by="researcher_a",
        added_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )

    assert update.evidence_role == evidence_role
    assert update.review_id == "review_2026_001"


def test_thread_update_requires_a_matching_link_review() -> None:
    with pytest.raises(ThreadValidationError, match="link_to_thread"):
        create_thread_update(
            thread_id="thread_supply_constraint",
            event_id="evt_2026_001",
            review=linked_review(thread_id="thread_other"),
            update_id="update_2026_001",
            evidence_role="supporting",
            summary="A synthetic summary.",
            event_date="2026-09-11",
            added_by="researcher_a",
            drafted_by="researcher_a",
        )


def test_thread_storage_is_private_and_append_only(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    record = thread()
    thread_path = write_thread(record, threads_directory)  # type: ignore[arg-type]
    update = create_thread_update(
        thread_id="thread_supply_constraint",
        event_id="evt_2026_001",
        review=linked_review(),
        update_id="update_2026_001",
        evidence_role="supporting",
        summary="A synthetic reviewed observation is relevant to the hypothesis.",
        event_date="2026-09-11",
        added_by="researcher_a",
        drafted_by="researcher_a",
        added_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    update_path = append_thread_update(update, threads_directory)

    assert yaml.safe_load(thread_path.read_text(encoding="utf-8"))["thread_id"] == (
        "thread_supply_constraint"
    )
    assert yaml.safe_load(update_path.read_text(encoding="utf-8"))["evidence_role"] == "supporting"
    with pytest.raises(FileExistsError, match="already exists"):
        append_thread_update(update, threads_directory)


def test_load_thread_and_updates_round_trip(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    write_thread(thread(), threads_directory)  # type: ignore[arg-type]
    append_thread_update(
        create_thread_update(
            thread_id="thread_supply_constraint",
            event_id="evt_2026_001",
            review=linked_review(),
            update_id="update_2026_001",
            evidence_role="supporting",
            summary="A synthetic supporting observation.",
            event_date="2026-09-11",
            added_by="researcher_a",
            drafted_by="researcher_a",
            added_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        ),
        threads_directory,
    )

    loaded_thread = load_thread(threads_directory / "thread_supply_constraint")
    updates = load_thread_updates(threads_directory / "thread_supply_constraint")

    assert loaded_thread.thread_id == "thread_supply_constraint"
    assert [update.update_id for update in updates] == ["update_2026_001"]


def test_load_thread_updates_orders_by_date_then_update_id(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    write_thread(thread(), threads_directory)  # type: ignore[arg-type]
    for update_id, event_date in (
        ("update_2026_003", "2026-09-12"),
        ("update_2026_001", "2026-09-11"),
        ("update_2026_002", "2026-09-11"),
    ):
        append_thread_update(
            create_thread_update(
                thread_id="thread_supply_constraint",
                event_id="evt_2026_001",
                review=linked_review(),
                update_id=update_id,
                evidence_role="supporting",
                summary="A synthetic observation.",
                event_date=event_date,
                added_by="researcher_a",
                drafted_by="researcher_a",
                added_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
            ),
            threads_directory,
        )

    updates = load_thread_updates(threads_directory / "thread_supply_constraint")

    assert [update.update_id for update in updates] == [
        "update_2026_001",
        "update_2026_002",
        "update_2026_003",
    ]


def test_list_thread_ids_is_sorted_and_empty_when_missing(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    assert list_thread_ids(threads_directory) == ()

    write_thread(thread(), threads_directory)  # type: ignore[arg-type]

    assert list_thread_ids(threads_directory) == ("thread_supply_constraint",)
