from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from signalweave.basket import load_basket
from signalweave.extract import TranscriptSegment
from signalweave.pipeline import PipelineError, run_pipeline
from signalweave.propose import DraftedStory, ModelIdentity
from signalweave.schema import load_candidate_event
from signalweave.threads import load_thread


REMOTE_IDENTITY = ModelIdentity(
    provider="anthropic", model_id="claude-synthetic-1", model_locality="remote"
)


class FakeCandidateProposer:
    """One candidate per segment; segment 2's cited_span is fabricated so the
    span-exists check rejects it, exercising the pipeline's per-segment skip.
    """

    def propose(self, segment: TranscriptSegment) -> Iterable[Mapping[str, Any]]:
        cited_span = (
            "This wording never appears in the segment."
            if segment.position == 2
            else segment.text
        )
        return (
            {
                "event_id": f"evt_synthetic_{segment.position:03d}",
                "date": "2026-09-11",
                "kind": "observation",
                "summary": f"A synthetic observation from segment {segment.position}.",
                "uncertainty": "medium",
                "cited_span": cited_span,
                "drafted_by": "model_claude_synthetic_1",
                "run_id": "run_propose_fake",
            },
        )


class FakeStoryProposer:
    def propose(self, summaries: list[str], *, input_id: str) -> DraftedStory:
        assert summaries  # never called with nothing to draft from
        return DraftedStory(
            mechanism="A synthetic mechanism.",
            open_question="A synthetic question?",
            invalidation_conditions=["A synthetic invalidation condition."],
            groups=["synthetic upstream suppliers"],
            market_sentiment="Synthetic cautiously positive sentiment.",
            drafted_by="model_claude_synthetic_1",
            run_id="run_story_fake",
        )


class FakeBasketProposer:
    def propose(self, story: DraftedStory, *, input_id: str) -> tuple[list[str], str]:
        return ["tsmc", "asml"], "run_basket_fake"


class EmptyCandidateProposer:
    def propose(self, segment: TranscriptSegment) -> Iterable[Mapping[str, Any]]:
        return ()


def _transcript(tmp_path: Path) -> Path:
    path = tmp_path / "private.md"
    path.write_text(
        "First synthetic paragraph is long enough to be a segment.\n\n"
        "Second synthetic paragraph is also long enough to be a segment.",
        encoding="utf-8",
    )
    return path


def _run(tmp_path: Path, *, candidate_proposer, privacy_tier: str = "remote"):
    return run_pipeline(
        _transcript(tmp_path),
        source="source_a",
        document_id="doc_2026_001",
        event_date="2026-09-11",
        privacy_tier=privacy_tier,
        candidate_proposer=candidate_proposer,
        story_proposer=FakeStoryProposer(),
        basket_proposer=FakeBasketProposer(),
        identity=REMOTE_IDENTITY,
        inbox_events_directory=tmp_path / "data" / "inbox" / "events",
        threads_directory=tmp_path / "data" / "private" / "threads",
    )


def test_pipeline_skips_a_segment_whose_span_check_fails_and_continues(tmp_path: Path) -> None:
    result = _run(tmp_path, candidate_proposer=FakeCandidateProposer())

    assert result.segments_total == 2
    assert result.segments_skipped == 1
    assert len(result.event_paths) == 1
    event = load_candidate_event(result.event_paths[0])
    assert event.event_id == "evt_synthetic_001"


def test_pipeline_stamps_every_record_unreviewed_with_drafted_by_and_run_id(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, candidate_proposer=FakeCandidateProposer())

    event = load_candidate_event(result.event_paths[0])
    assert event.review_status == "unreviewed"
    assert event.drafted_by == "model_claude_synthetic_1"
    assert event.run_id == "run_propose_fake"

    thread = load_thread(result.thread_path.parent)
    assert thread.review_status == "unreviewed"
    assert thread.drafted_by == "model_claude_synthetic_1"
    assert thread.run_id == "run_story_fake"

    basket = load_basket(result.thread_path.parent)
    assert basket.review_status == "unreviewed"
    assert basket.run_id == "run_basket_fake"
    assert basket.instruments == ("tsmc", "asml")


def test_pipeline_derives_thread_id_from_document_id(tmp_path: Path) -> None:
    result = _run(tmp_path, candidate_proposer=FakeCandidateProposer())

    assert result.thread_id == "story_doc_2026_001"


def test_pipeline_refuses_a_local_only_source_against_a_remote_model(tmp_path: Path) -> None:
    with pytest.raises(PipelineError, match="local-only"):
        _run(tmp_path, candidate_proposer=FakeCandidateProposer(), privacy_tier="local")


def test_pipeline_raises_when_no_events_survive_extraction(tmp_path: Path) -> None:
    with pytest.raises(PipelineError, match="no candidate events"):
        _run(tmp_path, candidate_proposer=EmptyCandidateProposer())


def test_pipeline_never_writes_segment_text_into_any_tracked_style_record(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, candidate_proposer=FakeCandidateProposer())

    thread_text = result.thread_path.read_text(encoding="utf-8")
    basket_text = result.basket_path.read_text(encoding="utf-8")
    assert "First synthetic paragraph" not in thread_text
    assert "First synthetic paragraph" not in basket_text
