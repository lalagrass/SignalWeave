from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import subprocess

import pytest
import yaml

from signalweave.basket import create_basket, write_basket
from signalweave.export import export_baskets, write_export
from signalweave.identifier_mapping import IdentifierMapping, write_identifier_mapping
from signalweave.runs import create_run, write_run
from signalweave.threads import create_thread, write_thread


def _mapping_member(instrument: str, index: int) -> dict[str, object]:
    if instrument == "unmapped":
        return {"declared_identifier": instrument, "mapping_status": "unresolved", "venue": None, "symbol": None, "reason": "No canonical listing supplied."}
    if instrument == "private_company":
        return {"declared_identifier": instrument, "mapping_status": "not_publicly_listed", "venue": None, "symbol": None, "reason": "Not publicly listed."}
    return {"declared_identifier": instrument, "mapping_status": "resolved", "venue": "TWSE", "symbol": f"{2300 + index}", "reason": None}


def seed_story(threads_directory: Path, *, thread_id: str, review_date: str, instruments: list[str], mapping_snapshot: bool = True) -> None:
    created_at = datetime(2026, 9, 11, tzinfo=timezone.utc)
    thread = create_thread(
        thread_id=thread_id, mechanism="Synthetic mechanism.", open_question="Synthetic question?",
        invalidation_conditions=["Synthetic invalidation condition."], groups=["synthetic upstream suppliers"],
        market_sentiment="Synthetic sentiment.", review_date=review_date, created_by="model_synthetic",
        drafted_by="model_synthetic", run_id="run_synthetic001", created_at=created_at,
    )
    write_thread(thread, threads_directory)
    basket = create_basket(thread_id=thread_id, instruments=instruments, drafted_by="model_synthetic", run_id="run_synthetic002", created_at=created_at)
    write_basket(basket, threads_directory)
    runs_directory = threads_directory.parent / "runs"
    for run_id, method_version, model_id in (("run_synthetic001", "story_v1", "synthetic-story"), ("run_synthetic002", "basket_v1", "synthetic-basket"), ("run_synthetic003", "identifier_mapping_v1", "synthetic-mapper")):
        write_run(create_run(provider="synthetic_provider", model_id=model_id, model_locality="local", method_version=method_version, input_id="synthetic_input", output="{}", run_id=run_id, created_at=created_at), runs_directory)
    if mapping_snapshot:
        mapping = IdentifierMapping.from_mapping(
            {
                "schema_version": 1, "mapping_id": "mapping_synthetic001", "supersedes_mapping_id": None,
                "thread_id": basket.thread_id, "basket_run_id": basket.run_id,
                "basket_created_at": basket.created_at.isoformat(),
                "members": [_mapping_member(item, index) for index, item in enumerate(instruments)],
                "provenance": {
                    "review_status": "unreviewed", "drafted_by": "mapping_agent_synthetic", "run_id": "run_synthetic003",
                    "provider": "synthetic_provider", "model_id": "synthetic-mapper", "model_locality": "local",
                    "method_version": "identifier_mapping_v1", "created_at": created_at.isoformat(),
                },
            }
        )
        write_identifier_mapping(mapping, threads_directory.parent / "identifier-mappings")


def _export(threads_directory: Path, as_of: date) -> list[dict[str, object]]:
    return export_baskets(threads_directory, threads_directory.parent / "runs", threads_directory.parent / "identifier-mappings", as_of=as_of)


def test_export_v2_emits_bound_members_and_independent_mapping_provenance(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-12-15", instruments=["tsmc", "unmapped", "private_company"])

    basket_path = threads_directory / "story_doc_2026_001" / "basket.yaml"
    basket_before = basket_path.read_bytes()
    entries = _export(threads_directory, date(2026, 9, 20))

    assert entries[0]["overdue"] is False
    basket = entries[0]["basket"]
    assert basket["members"] == [
        {"declared_identifier": "tsmc", "mapping_status": "resolved", "venue": "TWSE", "symbol": "2300", "reason": None},
        {"declared_identifier": "unmapped", "mapping_status": "unresolved", "venue": None, "symbol": None, "reason": "No canonical listing supplied."},
        {"declared_identifier": "private_company", "mapping_status": "not_publicly_listed", "venue": None, "symbol": None, "reason": "Not publicly listed."},
    ]
    assert basket["provenance"]["run_id"] == "run_synthetic002"
    assert basket["identifier_provenance"] == {
        "review_status": "unreviewed", "drafted_by": "mapping_agent_synthetic", "run_id": "run_synthetic003",
        "provider": "synthetic_provider", "model_id": "synthetic-mapper", "model_locality": "local",
        "method_version": "identifier_mapping_v1", "created_at": "2026-09-11T00:00:00+00:00",
    }
    assert basket_path.read_bytes() == basket_before


def test_export_v2_marks_overdue_and_preserves_an_empty_basket(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-09-01", instruments=[])

    entries = _export(threads_directory, date(2026, 9, 20))

    assert entries[0]["overdue"] is True
    assert entries[0]["basket"]["members"] == []


def test_write_export_is_schema_v2(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-12-15", instruments=["tsmc"])
    exports_directory = tmp_path / "data" / "private" / "exports"
    out_path = exports_directory / "baskets.yaml"

    written_path = write_export(_export(threads_directory, date(2026, 9, 20)), out_path, as_of=date(2026, 9, 20), private_exports_directories=(exports_directory,), generated_at=datetime(2026, 9, 20, tzinfo=timezone.utc))

    assert written_path == out_path
    loaded = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == 2
    assert loaded["as_of"] == "2026-09-20"
    assert loaded["stories"][0]["basket"]["members"][0]["declared_identifier"] == "tsmc"


def test_write_export_refuses_a_public_destination(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-12-15", instruments=[])

    with pytest.raises(ValueError, match="data/private/exports/"):
        write_export(_export(threads_directory, date(2026, 9, 20)), tmp_path / "public.yaml", as_of=date(2026, 9, 20), private_exports_directories=(tmp_path / "data" / "private" / "exports",))


def test_export_refuses_missing_snapshot_mapping(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-12-15", instruments=["tsmc"], mapping_snapshot=False)

    with pytest.raises(ValueError, match="no active identifier mapping"):
        _export(threads_directory, date(2026, 9, 20))


def test_synthetic_export_conforms_to_marketpulse_v2_reader_and_fixture(tmp_path: Path) -> None:
    marketpulse_root = Path(__file__).resolve().parents[2] / "MarketPulse"
    consumer_python = marketpulse_root / ".venv" / "bin" / "python"
    if not consumer_python.is_file():
        pytest.skip("MarketPulse checkout is not available for cross-repo contract verification")
    threads_directory = tmp_path / "data" / "private" / "threads"
    seed_story(threads_directory, thread_id="story_doc_2026_001", review_date="2026-12-15", instruments=["tsmc"])
    exports_directory = tmp_path / "data" / "private" / "exports"
    export_path = write_export(_export(threads_directory, date(2026, 9, 20)), exports_directory / "contract.yaml", as_of=date(2026, 9, 20), private_exports_directories=(exports_directory,), generated_at=datetime(2026, 9, 20, tzinfo=timezone.utc))
    code = "from pathlib import Path; import sys; from marketpulse.signalweave_import import load_signalweave_export; as_of, _, stories = load_signalweave_export(Path(sys.argv[1])); assert as_of.isoformat() == '2026-09-20'; assert stories[0].basket[0].symbol == '2300'"
    result = subprocess.run([str(consumer_python), "-c", code, str(export_path)], cwd=marketpulse_root, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr

    canonical = Path(__file__).parent / "fixtures" / "signalweave-export-v2.yaml"
    vendored = marketpulse_root / "tests" / "fixtures" / canonical.name
    assert canonical.read_bytes() == vendored.read_bytes()
