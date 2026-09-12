from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

import signalweave.cli as cli_module
from signalweave.cli import main
from signalweave.pipeline import REVIEW_CADENCE_DAYS

METHODS_SOURCE = Path(__file__).resolve().parent.parent / "methods"


class FakeAnthropicModelClient:
    """Stands in for `signalweave.propose.AnthropicModelClient`: never touches
    the network, returns one canned response per call in order.
    """

    _RESPONSES = [
        '[{"kind": "observation", "summary": "A synthetic observation.", '
        '"uncertainty": "medium", "cited_span": "Private source wording should '
        'never reach a tracked file."}]',
        '[{"kind": "observation", "summary": "A second synthetic observation.", '
        '"uncertainty": "medium", "cited_span": "A second synthetic paragraph '
        'makes the segment count deterministic."}]',
        '{"mechanism": "A synthetic mechanism.", "open_question": "A synthetic question?", '
        '"invalidation_conditions": ["A synthetic invalidation condition."], '
        '"groups": ["synthetic upstream suppliers"], '
        '"market_sentiment": "Synthetic cautiously positive sentiment."}',
        '{"instruments": ["tsmc", "asml"]}',
    ]

    def __init__(self, *, model_id: str) -> None:
        self.model_id = model_id
        self._responses = list(self._RESPONSES)

    def complete(self, prompt: str) -> str:
        return self._responses.pop(0)


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
review_status: unreviewed
uncertainty: medium
cited_span: A synthetic quoted span.
drafted_by: model_synthetic
run_id: run_synthetic001
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
review_status: unreviewed
uncertainty: medium
cited_span: A synthetic quoted span.
drafted_by: model_synthetic
run_id: run_synthetic001
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
                "--group",
                "synthetic upstream suppliers",
                "--market-sentiment",
                "Synthetic cautiously positive sentiment.",
                "--review-date",
                "2026-12-15",
                "--created-by",
                "researcher_a",
                "--drafted-by",
                "researcher_a",
                "--run-id",
                "run_synthetic001",
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
                "--drafted-by",
                "researcher_a",
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
    assert draft["cited_span"] == ""
    assert draft["review_status"] == "proposed"
    assert draft["drafted_by"] == "researcher_a"
    assert draft["run_id"] == "manual"

    assert main(["validate-event", str(draft_path)]) == 1
    assert "Event validation failed" in capsys.readouterr().out

    draft["kind"] = "evidence"
    draft["summary"] = "A synthetic observation."
    draft["uncertainty"] = "medium"
    draft["cited_span"] = "A synthetic quoted span the reviewer found themselves."
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
                "--drafted-by",
                "researcher_a",
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
        "--drafted-by",
        "researcher_a",
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
review_status: unreviewed
uncertainty: medium
cited_span: A synthetic quoted span.
drafted_by: model_synthetic
run_id: run_synthetic001
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
                "--group",
                "synthetic upstream suppliers",
                "--market-sentiment",
                "Synthetic cautiously positive sentiment.",
                "--review-date",
                "2026-12-15",
                "--created-by",
                "researcher_a",
                "--drafted-by",
                "agent_signalweave",
                "--run-id",
                "run_synthetic001",
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
                "--group",
                "synthetic upstream suppliers",
                "--market-sentiment",
                "Synthetic cautiously positive sentiment.",
                "--review-date",
                "2026-12-15",
                "--created-by",
                "researcher_a",
                "--drafted-by",
                "researcher_a",
                "--run-id",
                "run_synthetic001",
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


def test_run_pipeline_writes_events_story_and_basket_end_to_end(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(cli_module, "AnthropicModelClient", FakeAnthropicModelClient)
    shutil.copytree(METHODS_SOURCE, tmp_path / "methods")
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
                "run-pipeline",
                str(transcript),
                "--source",
                "source_a",
                "--document-id",
                "doc_2026_001",
                "--date",
                "2026-09-11",
                "--model-id",
                "claude-synthetic-1",
                "--privacy-tier",
                "remote",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "story_doc_2026_001" in output
    assert "Private source wording" not in output

    events_directory = tmp_path / "data" / "inbox" / "events"
    assert len(list(events_directory.glob("*.yaml"))) == 2
    thread_path = tmp_path / "data" / "private" / "threads" / "story_doc_2026_001" / "thread.yaml"
    basket_path = tmp_path / "data" / "private" / "threads" / "story_doc_2026_001" / "basket.yaml"
    assert thread_path.exists()
    assert basket_path.exists()
    assert "Private source wording" not in thread_path.read_text(encoding="utf-8")
    assert "Private source wording" not in basket_path.read_text(encoding="utf-8")
    runs_directory = tmp_path / "data" / "private" / "runs"
    assert len(list(runs_directory.glob("*.yaml"))) == 4


def test_run_pipeline_refuses_a_local_only_source(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_module, "AnthropicModelClient", FakeAnthropicModelClient)
    shutil.copytree(METHODS_SOURCE, tmp_path / "methods")
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
                "run-pipeline",
                str(transcript),
                "--source",
                "source_a",
                "--document-id",
                "doc_2026_001",
                "--date",
                "2026-09-11",
                "--model-id",
                "claude-synthetic-1",
                "--privacy-tier",
                "local",
            ]
        )
        == 1
    )
    assert "local-only" in capsys.readouterr().out


def test_export_baskets_writes_one_flat_basket_per_story(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(cli_module, "AnthropicModelClient", FakeAnthropicModelClient)
    shutil.copytree(METHODS_SOURCE, tmp_path / "methods")
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
                "run-pipeline",
                str(transcript),
                "--source",
                "source_a",
                "--document-id",
                "doc_2026_001",
                "--date",
                "2026-09-11",
                "--model-id",
                "claude-synthetic-1",
                "--privacy-tier",
                "remote",
            ]
        )
        == 0
    )
    capsys.readouterr()
    out_path = tmp_path / "export" / "baskets.yaml"

    assert main(["export-baskets", "--as-of", "2026-09-20", "--out", str(out_path)]) == 0
    assert "Exported 1 story" in capsys.readouterr().out

    expected_review_date = date.today() + timedelta(days=REVIEW_CADENCE_DAYS)
    exported = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert exported["stories"] == [
        {
            "thread_id": "story_doc_2026_001",
            "review_date": expected_review_date.isoformat(),
            "overdue": expected_review_date < date(2026, 9, 20),
            "basket": ["tsmc", "asml"],
        }
    ]


def test_append_thread_update_resolves_review_id_against_the_inbox(
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
review_status: unreviewed
uncertainty: medium
cited_span: A synthetic quoted span.
drafted_by: model_synthetic
run_id: run_synthetic001
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
                "--group",
                "synthetic upstream suppliers",
                "--market-sentiment",
                "Synthetic sentiment.",
                "--review-date",
                "2026-12-15",
                "--created-by",
                "researcher_a",
                "--drafted-by",
                "researcher_a",
                "--run-id",
                "run_synthetic001",
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
    capsys.readouterr()

    assert (
        main(
            [
                "append-thread-update",
                "--review-id",
                "review_2026_001",
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
                "researcher_a",
                "--added-at",
                "2026-09-11T00:00:00+00:00",
            ]
        )
        == 0
    )
    assert "Thread update recorded" in capsys.readouterr().out


def test_append_thread_update_requires_exactly_one_of_path_or_review_id(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "append-thread-update",
                "--thread",
                "thread_supply_constraint",
                "--event-id",
                "evt_2026_001",
                "--update-id",
                "update_2026_001",
                "--evidence-role",
                "supporting",
                "--summary",
                "A synthetic summary.",
                "--date",
                "2026-09-11",
                "--added-by",
                "researcher_a",
                "--drafted-by",
                "researcher_a",
            ]
        )
        == 1
    )
    assert "exactly one" in capsys.readouterr().out


def test_append_thread_update_names_an_unknown_thread_before_checking_the_review(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    # No review file exists at this path either — if the thread check did not
    # run first, this would fail with a review-loading error instead, naming
    # the wrong problem.
    missing_review = tmp_path / "does_not_exist.yaml"

    assert (
        main(
            [
                "append-thread-update",
                str(missing_review),
                "--thread",
                "thread_typo",
                "--event-id",
                "evt_2026_001",
                "--update-id",
                "update_2026_001",
                "--evidence-role",
                "supporting",
                "--summary",
                "A synthetic summary.",
                "--date",
                "2026-09-11",
                "--added-by",
                "researcher_a",
                "--drafted-by",
                "researcher_a",
            ]
        )
        == 1
    )
    assert "unknown thread: thread_typo" in capsys.readouterr().out


def test_help_documents_every_repeatable_flag(capsys) -> None:
    for command in ("create-thread",):
        with pytest.raises(SystemExit) as excinfo:
            main([command, "--help"])
        assert excinfo.value.code == 0
        output = capsys.readouterr().out
        assert "--invalidation-condition" in output
        assert "--group" in output
        assert output.count("repeated") == 2
