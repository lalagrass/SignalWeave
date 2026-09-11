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


def test_transcript_dry_run_never_echoes_private_source_text(tmp_path: Path, capsys) -> None:
    transcript = tmp_path / "private.md"
    transcript.write_text(
        "Private source wording should not appear in command output.\n\n"
        "A second synthetic paragraph makes the segment count deterministic.",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "extract-transcript",
                str(transcript),
                "--source",
                "source_a",
                "--document-id",
                "doc_2026_001",
                "--date",
                "2026-09-11",
                "--dry-run",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "2 segments, 0 candidates" in output
    assert "Private source wording" not in output


def test_review_event_writes_only_a_private_append_only_record(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    candidate = tmp_path / "candidate.yaml"
    candidate.write_text(
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
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "review-event",
                str(candidate),
                "--action",
                "link_to_thread",
                "--thread",
                "thread_supply_constraint",
                "--reviewer",
                "researcher_a",
                "--review-id",
                "review_2026_001",
                "--reviewed-at",
                "2026-09-11T00:00:00+00:00",
            ]
        )
        == 0
    )
    record = tmp_path / "data" / "inbox" / "reviews" / "review_2026_001.yaml"
    assert record.exists()
    assert "Event review recorded" in capsys.readouterr().out
