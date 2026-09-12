"""Publication guardrails for the tracked repository."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

DEFAULT_BLOCKED_SUFFIXES = {".srt", ".vtt", ".mp3", ".m4a", ".transcript"}
DEFAULT_BLOCKED_PARTS = {"data/raw", "data/inbox", "data/private"}

# Directories whose synthetic-only convention (ADR-0001) means a literal
# private-zone path in their content is a test fixture, not a real locator.
SYNTHETIC_CONTENT_ROOTS = {"tests", "examples"}

# A private-zone reference longer than its bare zone name, or one fixed
# schema subfolder below it, names something concrete: that concrete thing is
# a locator, and a locator is itself identifying.
PRIVATE_LOCATOR_PATTERN = re.compile(r"data/(?:raw|inbox|private)/[\w./-]*")
SAFE_PRIVATE_LOCATOR_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"^data/raw/$",
        r"^data/inbox/$",
        r"^data/inbox/events/$",
        r"^data/inbox/reviews/$",
        r"^data/private/$",
        r"^data/private/threads/$",
        r"^data/private/worklog/$",
        r"^data/private/runs/$",
    )
)


class PublicCheckConfigurationError(RuntimeError):
    """Raised when public-check cannot run because local setup is missing."""


def is_configured(root: Path) -> bool:
    """Whether a local private-term list has been set up for this workspace."""
    return (root / ".signalweave" / "private_terms.txt").is_file()


def require_configuration(root: Path, *, allow_unconfigured: bool) -> None:
    """Refuse to run a private-term scan that would silently be a no-op.

    `violations` treats a missing `private_terms.txt` as "no terms", so an
    unconfigured workspace would report a clean scan without ever looking for
    anything. Call this before `violations` from the CLI so that case fails
    loudly instead.
    """
    if allow_unconfigured or is_configured(root):
        return
    raise PublicCheckConfigurationError(
        "no .signalweave/private_terms.txt found, so the private-term scan "
        "would silently check nothing (see README.md 'Privacy and "
        "publishing'). Create that file, or pass --allow-unconfigured to run "
        "without one."
    )


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


def _private_locators(content: str) -> list[str]:
    """Return private-zone path references more specific than a bare zone."""
    found: list[str] = []
    for raw_candidate in PRIVATE_LOCATOR_PATTERN.findall(content):
        # Trailing sentence punctuation is prose, not part of the path.
        candidate = raw_candidate.rstrip(".,;:")
        if candidate and not any(
            pattern.match(candidate) for pattern in SAFE_PRIVATE_LOCATOR_PATTERNS
        ):
            found.append(candidate)
    return found


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
        if rel.split("/", 1)[0] not in SYNTHETIC_CONTENT_ROOTS:
            for locator in _private_locators(content):
                found.append(f"private-zone locator {locator!r} in {rel}")
    return found
