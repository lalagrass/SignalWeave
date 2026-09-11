from __future__ import annotations

import argparse
from pathlib import Path

from signalweave.public_check import violations
from signalweave.schema import EventValidationError, load_candidate_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="signalweave")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("public-check")
    validate_event = commands.add_parser(
        "validate-event", help="Validate a candidate event YAML file."
    )
    validate_event.add_argument("path", type=Path)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
