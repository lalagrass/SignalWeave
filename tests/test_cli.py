from __future__ import annotations

from pathlib import Path

import yaml

from signalweave.cli import main


def test_public_check_fails_loudly_when_unconfigured(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["public-check"]) == 1
    output = capsys.readouterr().out
    assert "Publication check not run" in output
    assert "private_terms.txt" in output


def test_public_check_allow_unconfigured_runs_anyway(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["public-check", "--allow-unconfigured"]) == 0
    assert "Publication check passed" in capsys.readouterr().out


def test_public_check_runs_when_configured(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    signalweave_dir = tmp_path / ".signalweave"
    signalweave_dir.mkdir()
    (signalweave_dir / "private_terms.txt").write_text("term\n", encoding="utf-8")

    assert main(["public-check"]) == 0
    assert "Publication check passed" in capsys.readouterr().out


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


def test_create_thread_writes_only_a_private_thread(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "create-thread",
                "--thread-id",
                "thread_supply_constraint",
                "--mechanism",
                "A synthetic mechanism.",
                "--open-question",
                "A synthetic question?",
                "--invalidation-condition",
                "A synthetic invalidation condition.",
                "--review-date",
                "2026-12-15",
                "--created-by",
                "researcher_a",
                "--drafted-by",
                "researcher_a",
                "--created-at",
                "2026-09-11T00:00:00+00:00",
            ]
        )
        == 0
    )

    record = tmp_path / "data" / "private" / "threads" / "thread_supply_constraint" / "thread.yaml"
    assert record.exists()
    assert "Thread created" in capsys.readouterr().out


def test_draft_event_writes_an_invalid_skeleton_until_a_human_fills_it_in(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    transcript = tmp_path / "private.md"
    transcript.write_text(
        "Private source wording should never reach a tracked file.\n\n"
        "A second synthetic paragraph makes the segment count deterministic.",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "draft-event",
                str(transcript),
                "--source",
                "source_a",
                "--document-id",
                "doc_2026_001",
                "--date",
                "2026-09-11",
                "--segment",
                "1",
                "--event-id",
                "evt_2026_001",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "Candidate draft written" in output
    assert "Private source wording" not in output

    draft_path = tmp_path / "data" / "inbox" / "events" / "evt_2026_001.yaml"
    draft_text = draft_path.read_text(encoding="utf-8")
    assert "Private source wording" not in draft_text
    draft = yaml.safe_load(draft_text)
    assert draft["source_locator"] == "doc_2026_001#segment_1"
    assert draft["kind"] == ""
    assert draft["summary"] == ""
    assert draft["uncertainty"] == ""
    assert draft["review_status"] == "proposed"

    assert main(["validate-event", str(draft_path)]) == 1
    assert "Event validation failed" in capsys.readouterr().out

    draft["kind"] = "evidence"
    draft["summary"] = "A synthetic observation."
    draft["uncertainty"] = "medium"
    draft_path.write_text(yaml.safe_dump(draft, sort_keys=False), encoding="utf-8")

    assert main(["validate-event", str(draft_path)]) == 0
    assert "Event validation passed: evt_2026_001" in capsys.readouterr().out


def test_draft_event_rejects_out_of_range_segment_without_leaking_text(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    transcript = tmp_path / "private.md"
    transcript.write_text(
        "Private wording that must never leave this file.\n\n"
        "A second synthetic paragraph makes the segment count deterministic.",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "draft-event",
                str(transcript),
                "--source",
                "source_a",
                "--document-id",
                "doc_2026_001",
                "--date",
                "2026-09-11",
                "--segment",
                "12",
                "--event-id",
                "evt_2026_001",
            ]
        )
        == 1
    )
    output = capsys.readouterr().out
    assert "between 1 and 2" in output
    assert "Private wording" not in output
    assert not (tmp_path / "data" / "inbox" / "events").exists()


def test_draft_event_refuses_to_overwrite_an_existing_draft(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    transcript = tmp_path / "private.md"
    transcript.write_text(
        "First synthetic paragraph is long enough to be a segment.\n\n"
        "Second synthetic paragraph is also long enough to be a segment.",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    args = [
        "draft-event",
        str(transcript),
        "--source",
        "source_a",
        "--document-id",
        "doc_2026_001",
        "--date",
        "2026-09-11",
        "--segment",
        "1",
        "--event-id",
        "evt_2026_001",
    ]

    assert main(args) == 0
    capsys.readouterr()
    assert main(args) == 1
    assert "already exists" in capsys.readouterr().out


def test_show_thread_prints_supporting_and_counter_evidence_separately(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
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
    assert (
        main(
            [
                "create-thread",
                "--thread-id",
                "thread_supply_constraint",
                "--mechanism",
                "A synthetic mechanism.",
                "--open-question",
                "A synthetic question?",
                "--invalidation-condition",
                "A synthetic invalidation condition.",
                "--review-date",
                "2026-12-15",
                "--created-by",
                "researcher_a",
                "--drafted-by",
                "agent_signalweave",
                "--created-at",
                "2026-09-11T00:00:00+00:00",
            ]
        )
        == 0
    )
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
    review_path = tmp_path / "data" / "inbox" / "reviews" / "review_2026_001.yaml"
    assert (
        main(
            [
                "append-thread-update",
                str(review_path),
                "--thread",
                "thread_supply_constraint",
                "--event-id",
                "evt_2026_001",
                "--update-id",
                "update_2026_001",
                "--evidence-role",
                "supporting",
                "--summary",
                "A synthetic reviewed observation supports the mechanism.",
                "--date",
                "2026-09-11",
                "--added-by",
                "researcher_a",
                "--drafted-by",
                "agent_signalweave",
                "--added-at",
                "2026-09-11T00:00:00+00:00",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["show-thread", "thread_supply_constraint"]) == 0
    output = capsys.readouterr().out

    assert "Mechanism: A synthetic mechanism." in output
    assert "Review date: 2026-12-15" in output
    assert "Created by: researcher_a (drafted by: agent_signalweave)" in output
    supporting_index = output.index("Supporting evidence:")
    counter_index = output.index("Counter evidence:")
    assert supporting_index < counter_index
    supporting_section = output[supporting_index:counter_index]
    assert (
        "A synthetic reviewed observation supports the mechanism." in supporting_section
    )
    assert "added by=researcher_a" in supporting_section
    assert "drafted by=agent_signalweave" in supporting_section
    assert "(none)" in output[counter_index:]
    assert "evt_2026_001" in output
    assert "review_2026_001" in output


def test_list_threads_marks_overdue_only_from_the_supplied_as_of_date(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    assert (
        main(
            [
                "create-thread",
                "--thread-id",
                "thread_supply_constraint",
                "--mechanism",
                "A synthetic mechanism.",
                "--open-question",
                "A synthetic question?",
                "--invalidation-condition",
                "A synthetic invalidation condition.",
                "--review-date",
                "2026-12-15",
                "--created-by",
                "researcher_a",
                "--drafted-by",
                "researcher_a",
                "--created-at",
                "2026-09-11T00:00:00+00:00",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["list-threads", "--as-of", "2026-09-11"]) == 0
    not_overdue_output = capsys.readouterr().out
    assert "OVERDUE" not in not_overdue_output
    assert "thread_supply_constraint" in not_overdue_output

    assert main(["list-threads", "--as-of", "2027-01-01"]) == 0
    overdue_output = capsys.readouterr().out
    assert "OVERDUE" in overdue_output
