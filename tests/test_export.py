from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from signalweave.basket import create_basket, write_basket
from signalweave.export import export_baskets, write_export
from signalweave.threads import create_thread, write_thread


def seed_story(
    threads_directory: Path,
    *,
    thread_id: str,
    review_date: str,
    instruments: list[str],
) -> None:
    thread = create_thread(
        thread_id=thread_id,
        mechanism="A synthetic mechanism that must never appear in the export.",
        open_question="A synthetic question?",
        invalidation_conditions=["A synthetic invalidation condition."],
        groups=["synthetic upstream suppliers"],
        market_sentiment="Synthetic sentiment that must never appear in the export.",
        review_date=review_date,
        created_by="model_synthetic",
        drafted_by="model_synthetic",
        run_id="run_synthetic001",
        created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    write_thread(thread, threads_directory)
    basket = create_basket(
        thread_id=thread_id,
        instruments=instruments,
        drafted_by="model_synthetic",
        run_id="run_synthetic002",
        created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    write_basket(basket, threads_directory)


def test_export_baskets_emits_one_flat_basket_per_story(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(
        threads_directory,
        thread_id="story_doc_2026_001",
        review_date="2026-12-15",
        instruments=["tsmc", "asml"],
    )

    entries = export_baskets(threads_directory, as_of=date(2026, 9, 20))

    assert entries == [
        {
            "thread_id": "story_doc_2026_001",
            "review_date": "2026-12-15",
            "overdue": False,
            "basket": ["tsmc", "asml"],
            "mechanism": "A synthetic mechanism that must never appear in the export.",
            "groups": ["synthetic upstream suppliers"],
            "market_sentiment": "Synthetic sentiment that must never appear in the export.",
        }
    ]


def test_export_baskets_marks_overdue_from_as_of(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(
        threads_directory,
        thread_id="story_doc_2026_001",
        review_date="2026-09-01",
        instruments=[],
    )

    entries = export_baskets(threads_directory, as_of=date(2026, 9, 20))

    assert entries[0]["overdue"] is True
    assert entries[0]["basket"] == []


def test_export_includes_mechanism_groups_and_market_sentiment(tmp_path: Path) -> None:
    """Corrected 2026-09-13: these are model-synthesized story fields, already
    shown by show-thread, not raw source text — the export is no longer
    missing them (see milestone-2-v0.md scope item 5's correction note)."""
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(
        threads_directory,
        thread_id="story_doc_2026_001",
        review_date="2026-12-15",
        instruments=["tsmc"],
    )

    entries = export_baskets(threads_directory, as_of=date(2026, 9, 20))

    assert set(entries[0].keys()) == {
        "thread_id",
        "review_date",
        "overdue",
        "basket",
        "mechanism",
        "groups",
        "market_sentiment",
    }
    assert entries[0]["mechanism"] == (
        "A synthetic mechanism that must never appear in the export."
    )
    assert entries[0]["groups"] == ["synthetic upstream suppliers"]
    assert entries[0]["market_sentiment"] == (
        "Synthetic sentiment that must never appear in the export."
    )
    # open_question and invalidation_conditions are still excluded — not asked for.
    assert "open_question" not in entries[0]
    assert "invalidation_conditions" not in entries[0]


def test_write_export_round_trips_via_yaml(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(
        threads_directory,
        thread_id="story_doc_2026_001",
        review_date="2026-12-15",
        instruments=["tsmc"],
    )
    entries = export_baskets(threads_directory, as_of=date(2026, 9, 20))
    out_path = tmp_path / "export" / "baskets.yaml"

    written_path = write_export(entries, out_path, as_of=date(2026, 9, 20))

    assert written_path == out_path
    loaded = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert loaded["as_of"] == "2026-09-20"
    assert loaded["stories"] == entries
