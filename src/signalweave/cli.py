from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from signalweave.extract import NoopCandidateProposer, extract_candidates, segment_transcript
from signalweave.public_check import violations
from signalweave.review import ReviewValidationError, create_review, write_review
from signalweave.schema import EventValidationError, load_candidate_event


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
