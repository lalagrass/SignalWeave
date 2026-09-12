from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from signalweave.runs import (
    Run,
    RunValidationError,
    create_run,
    load_run,
    new_run_id,
    write_run,
)


def run() -> Run:
    return create_run(
        provider="anthropic",
        model_id="claude-synthetic-1",
        model_locality="remote",
        method_version="propose_v1",
        input_id="doc_2026_001#segment_1",
        output='[{"kind": "observation"}]',
        run_id="run_synthetic001",
        created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )


def test_run_ids_are_not_content_derived() -> None:
    first = new_run_id()
    second = new_run_id()

    assert first != second
    assert first.startswith("run_")


def test_run_rejects_unknown_model_locality() -> None:
    with pytest.raises(RunValidationError, match="model_locality"):
        create_run(
            provider="anthropic",
            model_id="claude-synthetic-1",
            model_locality="orbital",
            method_version="propose_v1",
            input_id="doc_2026_001#segment_1",
            output="[]",
        )


def test_write_run_never_overwrites(tmp_path: Path) -> None:
    runs_directory = tmp_path / "data" / "private" / "runs"
    record = run()

    path = write_run(record, runs_directory)

    assert path == runs_directory / "run_synthetic001.yaml"
    with pytest.raises(FileExistsError, match="already exists"):
        write_run(record, runs_directory)


def test_run_round_trips_verbatim_output(tmp_path: Path) -> None:
    runs_directory = tmp_path / "data" / "private" / "runs"
    path = write_run(run(), runs_directory)

    loaded = load_run(path)

    assert loaded.output == '[{"kind": "observation"}]'
    assert loaded.provider == "anthropic"
    assert loaded.model_locality == "remote"
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["method_version"] == "propose_v1"
