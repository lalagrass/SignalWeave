from __future__ import annotations

from pathlib import Path

import pytest

from signalweave.extract import TranscriptSegment
from signalweave.propose import (
    DraftedStory,
    ModelBackedBasketProposer,
    ModelBackedCandidateProposer,
    ModelBackedStoryProposer,
    ModelIdentity,
    ProposeError,
    drafted_by_for,
    render_method,
)
from signalweave.runs import load_run


class FakeModelClient:
    """Returns a canned response per call; never touches a network."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._responses.pop(0)


IDENTITY = ModelIdentity(provider="anthropic", model_id="claude-synthetic-1", model_locality="remote")


def test_render_method_survives_literal_braces_in_the_template() -> None:
    template = 'Say {"kind": "x"} then use {segment_text}.'

    rendered = render_method(template, segment_text="hello")

    assert rendered == 'Say {"kind": "x"} then use hello.'


def test_drafted_by_for_produces_a_schema_safe_identifier() -> None:
    assert drafted_by_for("claude-opus-4-1-20250805") == "model_claude_opus_4_1_20250805"


def test_candidate_proposer_records_a_run_and_stamps_drafted_by_and_run_id(
    tmp_path: Path,
) -> None:
    client = FakeModelClient(
        [
            '[{"kind": "observation", "summary": "A synthetic summary.", '
            '"uncertainty": "medium", "cited_span": "Synthetic segment text."}]'
        ]
    )
    runs_directory = tmp_path / "data" / "private" / "runs"
    proposer = ModelBackedCandidateProposer(
        client,
        IDENTITY,
        method_template="Segment: {segment_text}",
        event_date="2026-09-11",
        runs_directory=runs_directory,
    )
    segment = TranscriptSegment(
        source="source_a",
        source_locator="doc_2026_001#segment_1",
        position=1,
        text="Synthetic segment text.",
    )

    proposals = list(proposer.propose(segment))

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["event_id"] == "evt_doc_2026_001_001_01"
    assert proposal["cited_span"] == "Synthetic segment text."
    assert proposal["drafted_by"] == "model_claude_synthetic_1"
    assert "Synthetic segment text." in client.prompts[0]

    run_files = list(runs_directory.glob("*.yaml"))
    assert len(run_files) == 1
    run = load_run(run_files[0])
    assert run.run_id == proposal["run_id"]
    assert run.provider == "anthropic"
    assert run.model_locality == "remote"
    assert run.input_id == "doc_2026_001#segment_1"


def test_candidate_proposer_handles_code_fenced_json(tmp_path: Path) -> None:
    client = FakeModelClient(["```json\n[]\n```"])
    proposer = ModelBackedCandidateProposer(
        client,
        IDENTITY,
        method_template="Segment: {segment_text}",
        event_date="2026-09-11",
        runs_directory=tmp_path / "runs",
    )
    segment = TranscriptSegment("source_a", "doc_2026_001#segment_1", 1, "Text.")

    assert list(proposer.propose(segment)) == []


def test_candidate_proposer_rejects_non_array_output(tmp_path: Path) -> None:
    client = FakeModelClient(['{"not": "an array"}'])
    proposer = ModelBackedCandidateProposer(
        client,
        IDENTITY,
        method_template="Segment: {segment_text}",
        event_date="2026-09-11",
        runs_directory=tmp_path / "runs",
    )
    segment = TranscriptSegment("source_a", "doc_2026_001#segment_1", 1, "Text.")

    with pytest.raises(ProposeError, match="JSON array"):
        list(proposer.propose(segment))


def test_story_proposer_returns_a_drafted_story_and_records_a_run(tmp_path: Path) -> None:
    client = FakeModelClient(
        [
            '{"mechanism": "A synthetic mechanism.", "open_question": "A synthetic question?", '
            '"invalidation_conditions": ["A synthetic invalidation condition."], '
            '"groups": ["synthetic upstream suppliers"], '
            '"market_sentiment": "Synthetic cautiously positive sentiment."}'
        ]
    )
    runs_directory = tmp_path / "data" / "private" / "runs"
    proposer = ModelBackedStoryProposer(
        client,
        IDENTITY,
        method_template="Observations: {observation_summaries}",
        runs_directory=runs_directory,
    )

    story = proposer.propose(["A synthetic observation."], input_id="doc_2026_001")

    assert isinstance(story, DraftedStory)
    assert story.mechanism == "A synthetic mechanism."
    assert story.groups == ["synthetic upstream suppliers"]
    assert story.drafted_by == "model_claude_synthetic_1"
    assert "A synthetic observation." in client.prompts[0]
    assert len(list(runs_directory.glob("*.yaml"))) == 1


def test_basket_proposer_returns_instruments_and_run_id(tmp_path: Path) -> None:
    client = FakeModelClient(['{"instruments": ["tsmc", "asml"]}'])
    runs_directory = tmp_path / "data" / "private" / "runs"
    proposer = ModelBackedBasketProposer(
        client,
        IDENTITY,
        method_template="Story: {mechanism} {groups} {market_sentiment}",
        runs_directory=runs_directory,
    )
    story = DraftedStory(
        mechanism="A synthetic mechanism.",
        open_question="A synthetic question?",
        invalidation_conditions=["A synthetic invalidation condition."],
        groups=["synthetic upstream suppliers"],
        market_sentiment="Synthetic sentiment.",
        drafted_by="model_claude_synthetic_1",
        run_id="run_story001",
    )

    instruments, run_id = proposer.propose(story, input_id="story_doc_2026_001")

    assert instruments == ["tsmc", "asml"]
    assert run_id != "run_story001"
    assert len(list(runs_directory.glob("*.yaml"))) == 1


def test_basket_proposer_rejects_missing_instruments_field(tmp_path: Path) -> None:
    client = FakeModelClient(["{}"])
    proposer = ModelBackedBasketProposer(
        client,
        IDENTITY,
        method_template="Story: {mechanism} {groups} {market_sentiment}",
        runs_directory=tmp_path / "runs",
    )
    story = DraftedStory(
        mechanism="m",
        open_question="q",
        invalidation_conditions=["c"],
        groups=["g"],
        market_sentiment="s",
        drafted_by="model_x",
        run_id="run_story001",
    )

    with pytest.raises(ProposeError, match="instruments"):
        proposer.propose(story, input_id="story_doc_2026_001")
