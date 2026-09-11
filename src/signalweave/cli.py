from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from signalweave.extract import NoopCandidateProposer, extract_candidates, segment_transcript
from signalweave.public_check import violations
from signalweave.review import (
    ReviewValidationError,
    create_review,
    load_review,
    write_review,
)
from signalweave.schema import EventValidationError, load_candidate_event
from signalweave.threads import (
    ThreadValidationError,
    append_thread_update,
    create_thread,
    create_thread_update,
    write_thread,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="signalweave")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("public-check")
    validate_event = commands.add_parser(
        "validate-event", help="Validate a candidate event YAML file."
    )
    validate_event.add_argument("path", type=Path)
    extract_transcript = commands.add_parser(
        "extract-transcript",
        help="Segment a private transcript and report a no-write extraction dry run.",
    )
    extract_transcript.add_argument("path", type=Path)
    extract_transcript.add_argument("--source", required=True)
    extract_transcript.add_argument("--document-id", required=True)
    extract_transcript.add_argument("--date", required=True, dest="event_date")
    extract_transcript.add_argument("--dry-run", action="store_true")
    review_event = commands.add_parser(
        "review-event", help="Append a private human review record for a candidate event."
    )
    review_event.add_argument("path", type=Path)
    review_event.add_argument("--action", required=True)
    review_event.add_argument("--reviewer", required=True)
    review_event.add_argument("--review-id", required=True)
    review_event.add_argument("--reviewed-at")
    review_event.add_argument("--reason")
    review_event.add_argument("--thread", dest="suggested_thread")
    create_thread_command = commands.add_parser(
        "create-thread", help="Create a private, human-owned research thread."
    )
    create_thread_command.add_argument("--thread-id", required=True)
    create_thread_command.add_argument("--mechanism", required=True)
    create_thread_command.add_argument("--open-question", required=True)
    create_thread_command.add_argument("--invalidation-condition", action="append", required=True)
    create_thread_command.add_argument("--review-date", required=True)
    create_thread_command.add_argument("--created-by", required=True)
    create_thread_command.add_argument("--created-at")
    append_update = commands.add_parser(
        "append-thread-update", help="Append private evidence to a linked research thread."
    )
    append_update.add_argument("review_path", type=Path)
    append_update.add_argument("--thread", required=True, dest="thread_id")
    append_update.add_argument("--event-id", required=True)
    append_update.add_argument("--update-id", required=True)
    append_update.add_argument("--evidence-role", required=True)
    append_update.add_argument("--summary", required=True)
    append_update.add_argument("--date", required=True, dest="event_date")
    append_update.add_argument("--added-by", required=True)
    append_update.add_argument("--added-at")
    args = parser.parse_args(argv)

    if args.command == "public-check":
        problems = violations(Path.cwd())
        if problems:
            print("Publication check failed:")
            print("\n".join(f"- {problem}" for problem in problems))
            return 1
        print("Publication check passed (human review still required).")
    elif args.command == "validate-event":
        try:
            event = load_candidate_event(args.path)
        except (EventValidationError, OSError) as error:
            print(f"Event validation failed: {error}")
            return 1
        print(f"Event validation passed: {event.event_id}")
    elif args.command == "extract-transcript":
        if not args.dry_run:
            print("Extraction requires --dry-run until a reviewed proposer is configured.")
            return 1
        try:
            date.fromisoformat(args.event_date)
            segments = segment_transcript(
                args.path.read_text(encoding="utf-8"),
                source=args.source,
                document_id=args.document_id,
            )
            candidates = extract_candidates(segments, NoopCandidateProposer())
        except (EventValidationError, OSError, UnicodeDecodeError, ValueError) as error:
            print(f"Transcript dry run failed: {error}")
            return 1
        print(f"Transcript dry run: {len(segments)} segments, {len(candidates)} candidates.")
    elif args.command == "review-event":
        try:
            reviewed_at = (
                datetime.fromisoformat(args.reviewed_at) if args.reviewed_at is not None else None
            )
            record = create_review(
                load_candidate_event(args.path),
                review_id=args.review_id,
                action=args.action,
                reviewer=args.reviewer,
                reviewed_at=reviewed_at,
                reason=args.reason,
                suggested_thread=args.suggested_thread,
            )
            path = write_review(record, Path.cwd() / "data" / "inbox" / "reviews")
        except (
            EventValidationError,
            ReviewValidationError,
            OSError,
            UnicodeDecodeError,
            ValueError,
        ) as error:
            print(f"Event review failed: {error}")
            return 1
        print(f"Event review recorded: {path}")
    elif args.command == "create-thread":
        try:
            created_at = (
                datetime.fromisoformat(args.created_at) if args.created_at is not None else None
            )
            thread = create_thread(
                thread_id=args.thread_id,
                mechanism=args.mechanism,
                open_question=args.open_question,
                invalidation_conditions=args.invalidation_condition,
                review_date=args.review_date,
                created_by=args.created_by,
                created_at=created_at,
            )
            path = write_thread(thread, Path.cwd() / "data" / "private" / "threads")
        except (ThreadValidationError, OSError, ValueError) as error:
            print(f"Thread creation failed: {error}")
            return 1
        print(f"Thread created: {path}")
    elif args.command == "append-thread-update":
        try:
            added_at = (
                datetime.fromisoformat(args.added_at) if args.added_at is not None else None
            )
            update = create_thread_update(
                thread_id=args.thread_id,
                event_id=args.event_id,
                review=load_review(args.review_path),
                update_id=args.update_id,
                evidence_role=args.evidence_role,
                summary=args.summary,
                event_date=args.event_date,
                added_by=args.added_by,
                added_at=added_at,
            )
            path = append_thread_update(update, Path.cwd() / "data" / "private" / "threads")
        except (ReviewValidationError, ThreadValidationError, OSError, UnicodeDecodeError, ValueError) as error:
            print(f"Thread update failed: {error}")
            return 1
        print(f"Thread update recorded: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
