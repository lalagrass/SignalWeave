from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import subprocess

import yaml
import pytest

from signalweave.basket import create_basket, write_basket
from signalweave.export import export_baskets, write_export
from signalweave.runs import create_run, write_run
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
    runs_directory = threads_directory.parent / "runs"
    write_run(
        create_run(
            provider="synthetic", model_id="synthetic-story", model_locality="local",
            method_version="story_v1", input_id="synthetic_story", output="{}",
            run_id="run_synthetic001", created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        ),
        runs_directory,
    )
    write_run(
        create_run(
            provider="synthetic", model_id="synthetic-basket", model_locality="local",
            method_version="basket_v1", input_id="synthetic_basket", output="{}",
            run_id="run_synthetic002", created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        ),
        runs_directory,
    )


def _export(threads_directory: Path, as_of: date) -> list[dict[str, object]]:
    return export_baskets(threads_directory, threads_directory.parent / "runs", as_of=as_of)


def test_export_baskets_emits_one_flat_basket_per_story(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(
        threads_directory,
        thread_id="story_doc_2026_001",
        review_date="2026-12-15",
        instruments=["tsmc", "asml"],
    )

    entries = _export(threads_directory, date(2026, 9, 20))

    assert entries == [
        {
            "thread_id": "story_doc_2026_001",
            "review_date": "2026-12-15",
            "overdue": False,
            "mechanism": "A synthetic mechanism that must never appear in the export.",
            "groups": ["synthetic upstream suppliers"],
            "market_sentiment": "Synthetic sentiment that must never appear in the export.",
            "provenance": {
                "review_status": "unreviewed", "drafted_by": "model_synthetic",
                "run_id": "run_synthetic001", "method_version": "story_v1",
            },
            "basket": {
                "instruments": ["tsmc", "asml"],
                "provenance": {
                    "review_status": "unreviewed", "drafted_by": "model_synthetic",
                    "run_id": "run_synthetic002", "method_version": "basket_v1",
                },
            },
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

    entries = _export(threads_directory, date(2026, 9, 20))

    assert entries[0]["overdue"] is True
    assert entries[0]["basket"]["instruments"] == []


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

    entries = _export(threads_directory, date(2026, 9, 20))

    assert set(entries[0].keys()) == {
        "thread_id",
        "review_date",
        "overdue",
        "mechanism",
        "groups",
        "market_sentiment", "provenance", "basket",
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
    entries = _export(threads_directory, date(2026, 9, 20))
    out_path = tmp_path / "export" / "baskets.yaml"

    exports_directory = tmp_path / "data" / "private" / "exports"
    out_path = exports_directory / "baskets.yaml"
    written_path = write_export(
        entries, out_path, as_of=date(2026, 9, 20),
        private_exports_directories=(exports_directory,),
        generated_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
    )

    assert written_path == out_path
    loaded = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == 1
    assert loaded["as_of"] == "2026-09-20"
    assert loaded["generated_at"] == "2026-09-20T00:00:00+00:00"
    assert loaded["stories"] == entries


def test_write_export_refuses_a_public_destination(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-12-15", instruments=[])

    with pytest.raises(ValueError, match="data/private/exports/"):
        write_export(
            _export(threads_directory, date(2026, 9, 20)),
            tmp_path / "public.yaml",
            as_of=date(2026, 9, 20),
            private_exports_directories=(tmp_path / "data" / "private" / "exports",),
        )


def test_write_export_allows_the_private_marketpulse_landing_zone(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-12-15", instruments=[])
    marketpulse_exports = tmp_path / "MarketPulse" / "data" / "private" / "signalweave"

    written = write_export(
        _export(threads_directory, date(2026, 9, 20)),
        marketpulse_exports / "contract.yaml",
        as_of=date(2026, 9, 20),
        private_exports_directories=(
            tmp_path / "data" / "private" / "exports", marketpulse_exports
        ),
    )

    assert written == (marketpulse_exports / "contract.yaml").resolve()


def test_synthetic_export_conforms_to_marketpulse_reader(tmp_path: Path) -> None:
    """The neighboring consumer parses a producer-written synthetic v1 export."""
    marketpulse_root = Path(__file__).resolve().parents[2] / "MarketPulse"
    consumer_python = marketpulse_root / ".venv" / "bin" / "python"
    if not consumer_python.is_file():
        pytest.skip("MarketPulse checkout is not available for cross-repo contract verification")

    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(
        threads_directory,
        thread_id="story_doc_2026_001",
        review_date="2026-12-15",
        instruments=["tsmc"],
    )
    exports_directory = tmp_path / "data" / "private" / "exports"
    export_path = write_export(
        _export(threads_directory, date(2026, 9, 20)),
        exports_directory / "contract.yaml",
        as_of=date(2026, 9, 20),
        private_exports_directories=(exports_directory,),
        generated_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
    )
    code = (
        "from pathlib import Path; "
        "from marketpulse.signalweave_import import load_signalweave_export; "
        "as_of, generated_at, stories = load_signalweave_export(Path(sys.argv[1])); "
        "assert as_of.isoformat() == '2026-09-20'; "
        "assert generated_at.isoformat() == '2026-09-20T00:00:00+00:00'; "
        "assert stories[0].provenance.review_status == 'unreviewed'; "
        "assert stories[0].basket_provenance.method_version == 'basket_v1'"
    )
    result = subprocess.run(
        [str(consumer_python), "-c", "import sys; " + code, str(export_path)],
        cwd=marketpulse_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    canonical = Path(__file__).parent / "fixtures" / "signalweave-export-v1.yaml"
    vendored = marketpulse_root / "tests" / "fixtures" / canonical.name
    assert canonical.read_bytes() == vendored.read_bytes()


def test_export_refuses_missing_provenance_run(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-12-15", instruments=[])
    (threads_directory.parent / "runs" / "run_synthetic002.yaml").unlink()

    with pytest.raises(FileNotFoundError):
        _export(threads_directory, date(2026, 9, 20))
