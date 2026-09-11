from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from signalweave.extract import (
    NoopCandidateProposer,
    draft_candidate_event,
    extract_candidates,
    segment_transcript,
    select_segment,
    write_candidate_draft,
)
from signalweave.public_check import (
    PublicCheckConfigurationError,
    require_configuration,
    violations,
)
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
    list_thread_ids,
    load_thread,
    load_thread_updates,
    write_thread,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="signalweave")
    commands = parser.add_subparsers(dest="command", required=True)
    public_check_command = commands.add_parser("public-check")
    public_check_command.add_argument(
        "--allow-unconfigured",
        action="store_true",
        help="Run without a .signalweave/private_terms.txt (for a genuinely termless repo).",
    )
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
    create_thread_command.add_argument("--drafted-by", required=True)
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
    append_update.add_argument("--drafted-by", required=True)
    append_update.add_argument("--added-at")
    draft_event = commands.add_parser(
        "draft-event",
        help="Write a pre-filled candidate card skeleton into the private inbox.",
    )
    draft_event.add_argument("path", type=Path)
    draft_event.add_argument("--source", required=True)
    draft_event.add_argument("--document-id", required=True)
    draft_event.add_argument("--date", required=True, dest="event_date")
    draft_event.add_argument("--segment", required=True, type=int, dest="segment_position")
    draft_event.add_argument("--event-id", required=True)
    show_thread = commands.add_parser(
        "show-thread", help="Print a private thread's header and its updates."
    )
    show_thread.add_argument("thread_id")
    list_threads_command = commands.add_parser(
        "list-threads", help="List private threads and mark those overdue as of a given date."
    )
    list_threads_command.add_argument("--as-of", required=True, dest="as_of")
    args = parser.parse_args(argv)

    if args.command == "public-check":
        try:
            require_configuration(Path.cwd(), allow_unconfigured=args.allow_unconfigured)
        except PublicCheckConfigurationError as error:
            print(f"Publication check not run: {error}")
            return 1
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
                drafted_by=args.drafted_by,
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
                drafted_by=args.drafted_by,
                added_at=added_at,
            )
            path = append_thread_update(update, Path.cwd() / "data" / "private" / "threads")
        except (ReviewValidationError, ThreadValidationError, OSError, UnicodeDecodeError, ValueError) as error:
            print(f"Thread update failed: {error}")
            return 1
        print(f"Thread update recorded: {path}")
    elif args.command == "draft-event":
        try:
            date.fromisoformat(args.event_date)
            segments = segment_transcript(
                args.path.read_text(encoding="utf-8"),
                source=args.source,
                document_id=args.document_id,
            )
            segment = select_segment(segments, args.segment_position)
            record = draft_candidate_event(
                segment, event_id=args.event_id, event_date=args.event_date
            )
            path = write_candidate_draft(record, Path.cwd() / "data" / "inbox" / "events")
        except (EventValidationError, OSError, UnicodeDecodeError, ValueError) as error:
            print(f"Draft event failed: {error}")
            return 1
        print(f"Candidate draft written: {path}")
    elif args.command == "show-thread":
        try:
            thread_directory = Path.cwd() / "data" / "private" / "threads" / args.thread_id
            thread = load_thread(thread_directory)
            updates = load_thread_updates(thread_directory)
        except (ThreadValidationError, OSError, UnicodeDecodeError, ValueError) as error:
            print(f"Show thread failed: {error}")
            return 1
        print(f"Thread: {thread.thread_id}")
        print(f"Mechanism: {thread.mechanism}")
        print(f"Open question: {thread.open_question}")
        print("Invalidation conditions:")
        for condition in thread.invalidation_conditions:
            print(f"- {condition}")
        print(f"Review date: {thread.review_date.isoformat()}")
        print(f"Created by: {thread.created_by} (drafted by: {thread.drafted_by})")
        for heading, role in (("Supporting evidence", "supporting"), ("Counter evidence", "counter")):
            print(f"\n{heading}:")
            role_updates = [update for update in updates if update.evidence_role == role]
            if not role_updates:
                print("(none)")
                continue
            for update in role_updates:
                print(
                    f"- {update.date.isoformat()} {update.summary} "
                    f"(event={update.event_id}, review={update.review_id}, "
                    f"added by={update.added_by}, drafted by={update.drafted_by})"
                )
    elif args.command == "list-threads":
        try:
            as_of = date.fromisoformat(args.as_of)
            threads_directory = Path.cwd() / "data" / "private" / "threads"
            lines = []
            for thread_id in list_thread_ids(threads_directory):
                thread_directory = threads_directory / thread_id
                thread = load_thread(thread_directory)
                updates = load_thread_updates(thread_directory)
                overdue = " OVERDUE" if thread.review_date < as_of else ""
                lines.append(
                    f"{thread.thread_id} review_date={thread.review_date.isoformat()} "
                    f"updates={len(updates)}{overdue}"
                )
        except (ThreadValidationError, OSError, UnicodeDecodeError, ValueError) as error:
            print(f"List threads failed: {error}")
            return 1
        print("\n".join(lines) if lines else "No threads found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
