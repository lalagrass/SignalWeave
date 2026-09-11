from __future__ import annotations

import argparse
from pathlib import Path

from signalweave.public_check import violations


def main() -> int:
    parser = argparse.ArgumentParser(prog="signalweave")
    parser.add_argument("command", choices=("public-check",))
    args = parser.parse_args()
    if args.command == "public-check":
        problems = violations(Path.cwd())
        if problems:
            print("Publication check failed:")
            print("\n".join(f"- {problem}" for problem in problems))
            return 1
        print("Publication check passed (human review still required).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

