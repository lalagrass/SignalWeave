"""Publication guardrails for the tracked repository."""

from __future__ import annotations

from pathlib import Path
import subprocess

DEFAULT_BLOCKED_SUFFIXES = {".srt", ".vtt", ".mp3", ".m4a", ".transcript"}
DEFAULT_BLOCKED_PARTS = {"data/raw", "data/inbox", "data/private"}


def private_terms(root: Path) -> list[str]:
    path = root / ".signalweave" / "private_terms.txt"
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def public_paths(root: Path) -> list[Path]:
    """Files Git would publish: tracked plus non-ignored, untracked files.

    Local raw sources are intentionally ignored, so a normal research workspace
    can contain them without making a release check unusable. A raw file added
    with `git add -f` is tracked and will therefore still be inspected.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return [path for path in root.rglob("*") if path.is_file()]
    return [root / item for item in result.stdout.decode().split("\0") if item]


def violations(root: Path, *, paths: list[Path] | None = None) -> list[str]:
    """Return publish-blocking paths and configured private-term matches."""
    terms = private_terms(root)
    found: list[str] = []
    for path in paths if paths is not None else public_paths(root):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel == blocked or rel.startswith(f"{blocked}/") for blocked in DEFAULT_BLOCKED_PARTS):
            found.append(f"blocked private path: {rel}")
            continue
        if path.suffix.lower() in DEFAULT_BLOCKED_SUFFIXES:
            found.append(f"blocked source format: {rel}")
            continue
        if rel in {".signalweave/private_terms.txt", ".signalweave/identity_map.yaml"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for term in terms:
            if term.casefold() in content.casefold():
                found.append(f"private term {term!r} in {rel}")
    return found
