from __future__ import annotations

from pathlib import Path

from signalweave.cli import main


def test_validate_event_accepts_a_valid_synthetic_yaml(tmp_path: Path, capsys) -> None:
    event = tmp_path / "event.yaml"
    event.write_text(
        """event_id: evt_2026_001
source: source_a
source_locator: doc_2026_001#segment_12
date: 2026-09-11
kind: evidence
summary: A synthetic observation.
review_status: proposed
uncertainty: medium
""",
        encoding="utf-8",
    )

    assert main(["validate-event", str(event)]) == 0
    assert "Event validation passed: evt_2026_001" in capsys.readouterr().out


def test_validate_event_reports_field_errors(tmp_path: Path, capsys) -> None:
    event = tmp_path / "event.yaml"
    event.write_text("event_id: evt_2026_001\n", encoding="utf-8")

    assert main(["validate-event", str(event)]) == 1
    assert "missing required field(s)" in capsys.readouterr().out
