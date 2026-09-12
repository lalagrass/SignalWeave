"""Deterministic orchestration: segment -> propose -> span check -> story -> basket.

Model calls happen inside fixed steps; there is no agent loop deciding what to
do next. Every record this produces is stamped `review_status: unreviewed`
with its `drafted_by` and its `run_id`, unconditionally (ADR-0008) — none of
this is optional or conditional on a later human step, because that step does
not exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from signalweave.basket import create_basket, write_basket
from signalweave.extract import extract_candidates, segment_transcript, write_candidate_draft
from signalweave.propose import (
    ModelBackedBasketProposer,
    ModelBackedCandidateProposer,
    ModelBackedStoryProposer,
    ModelIdentity,
    drafted_by_for,
)
from signalweave.schema import EventValidationError
from signalweave.threads import create_thread, write_thread


# How far out a freshly drafted story is scheduled to be looked at again.
# Not derived from anything in the source; a fixed operational cadence until
# milestone 3 gives baskets their own dated-change mechanism.
REVIEW_CADENCE_DAYS = 14


class PipelineError(RuntimeError):
    """Raised when the pipeline cannot proceed at all (not a per-segment skip)."""


@dataclass(frozen=True)
class PipelineResult:
    thread_id: str
    event_paths: tuple[Path, ...]
    thread_path: Path
    basket_path: Path
    segments_total: int
    segments_skipped: int


def run_pipeline(
    transcript_path: Path,
    *,
    source: str,
    document_id: str,
    event_date: str,
    privacy_tier: str,
    candidate_proposer: ModelBackedCandidateProposer,
    story_proposer: ModelBackedStoryProposer,
    basket_proposer: ModelBackedBasketProposer,
    identity: ModelIdentity,
    inbox_events_directory: Path,
    threads_directory: Path,
) -> PipelineResult:
    """Run one document through the full pipeline and write every record.

    `privacy_tier` ("local" or "remote") is the caller's declared handling for
    this source; if it is `"local"` and `identity.model_locality` is
    `"remote"`, this refuses before making any model call (ADR-0009: that
    refusal is an error, not a warning).
    """
    if privacy_tier not in {"local", "remote"}:
        raise PipelineError("privacy_tier must be 'local' or 'remote'")
    if privacy_tier == "local" and identity.model_locality == "remote":
        raise PipelineError(
            "source is marked local-only; refusing to send it to a remote model provider"
        )

    segments = segment_transcript(
        transcript_path.read_text(encoding="utf-8"), source=source, document_id=document_id
    )

    event_paths: list[Path] = []
    summaries: list[str] = []
    skipped = 0
    for segment in segments:
        try:
            candidates = extract_candidates((segment,), candidate_proposer)
        except EventValidationError:
            skipped += 1
            continue
        for candidate in candidates:
            path = write_candidate_draft(candidate.to_mapping(), inbox_events_directory)
            event_paths.append(path)
            summaries.append(candidate.summary)

    if not summaries:
        raise PipelineError(
            "no candidate events survived extraction; nothing to draft a story from"
        )

    thread_id = f"story_{document_id}"
    story = story_proposer.propose(summaries, input_id=document_id)
    instruments, basket_run_id = basket_proposer.propose(story, input_id=thread_id)

    created_at = datetime.now(timezone.utc)
    thread = create_thread(
        thread_id=thread_id,
        mechanism=story.mechanism,
        open_question=story.open_question,
        invalidation_conditions=story.invalidation_conditions,
        groups=story.groups,
        market_sentiment=story.market_sentiment,
        review_date=(created_at.date() + timedelta(days=REVIEW_CADENCE_DAYS)).isoformat(),
        created_by=story.drafted_by,
        drafted_by=story.drafted_by,
        run_id=story.run_id,
        created_at=created_at,
    )
    thread_path = write_thread(thread, threads_directory)

    basket = create_basket(
        thread_id=thread_id,
        instruments=instruments,
        drafted_by=drafted_by_for(identity.model_id),
        run_id=basket_run_id,
        created_at=created_at,
    )
    basket_path = write_basket(basket, threads_directory)

    return PipelineResult(
        thread_id=thread_id,
        event_paths=tuple(event_paths),
        thread_path=thread_path,
        basket_path=basket_path,
        segments_total=len(segments),
        segments_skipped=skipped,
    )
