"""Immutable pipeline run records (ADR-0009).

One file per model call: which model and provider produced it, whether the
call was local or remote, which method/prompt version drove it, what was fed
in, and its verbatim output. A run is never overwritten — re-running the same
step writes a new file — so a later model can be compared against what an
earlier one produced on the same input. Filenames are caller-supplied ids,
never a hash of the content (no content addressing): the point is traceability
per call, not deduplication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

import yaml

from signalweave.schema import IDENTIFIER


MODEL_LOCALITIES = frozenset({"local", "remote"})
REQUIRED_FIELDS = frozenset(
    {
        "run_id",
        "provider",
        "model_id",
        "model_locality",
        "method_version",
        "input_id",
        "output",
        "created_at",
    }
)


class RunValidationError(ValueError):
    """Raised when a run record does not meet its contract."""


@dataclass(frozen=True)
class Run:
    """One immutable, individually storable model call."""

    run_id: str
    provider: str
    model_id: str
    model_locality: str
    method_version: str
    input_id: str
    output: str
    created_at: datetime

    @classmethod
    def from_mapping(cls, record: dict[str, Any]) -> "Run":
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            raise RunValidationError(f"missing required field(s): {', '.join(missing)}")
        unknown = sorted(record.keys() - REQUIRED_FIELDS)
        if unknown:
            raise RunValidationError(f"unknown field(s): {', '.join(unknown)}")

        model_locality = _non_empty_string(record["model_locality"], "model_locality")
        if model_locality not in MODEL_LOCALITIES:
            raise RunValidationError(
                f"model_locality must be one of: {', '.join(sorted(MODEL_LOCALITIES))}"
            )
        output = record["output"]
        if not isinstance(output, str):
            raise RunValidationError("output must be a string")

        return cls(
            run_id=_identifier(record["run_id"], "run_id"),
            provider=_identifier(record["provider"], "provider"),
            model_id=_non_empty_string(record["model_id"], "model_id"),
            model_locality=model_locality,
            method_version=_identifier(record["method_version"], "method_version"),
            input_id=_non_empty_string(record["input_id"], "input_id"),
            output=output,
            created_at=_datetime(record["created_at"], "created_at"),
        )

    def to_mapping(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "provider": self.provider,
            "model_id": self.model_id,
            "model_locality": self.model_locality,
            "method_version": self.method_version,
            "input_id": self.input_id,
            "output": self.output,
            "created_at": self.created_at.isoformat(),
        }


def new_run_id() -> str:
    """A run id with no relation to run content — deliberately not a hash."""
    return f"run_{uuid.uuid4().hex}"


def create_run(
    *,
    provider: str,
    model_id: str,
    model_locality: str,
    method_version: str,
    input_id: str,
    output: str,
    run_id: str | None = None,
    created_at: datetime | None = None,
) -> Run:
    """Build one run record. `run_id` defaults to a fresh, content-free id."""
    return Run.from_mapping(
        {
            "run_id": run_id or new_run_id(),
            "provider": provider,
            "model_id": model_id,
            "model_locality": model_locality,
            "method_version": method_version,
            "input_id": input_id,
            "output": output,
            "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        }
    )


def write_run(run: Run, runs_directory: Path) -> Path:
    """Write one run record. Runs are immutable: never overwritten, ever."""
    runs_directory.mkdir(parents=True, exist_ok=True)
    path = runs_directory / f"{run.run_id}.yaml"
    if path.exists():
        raise FileExistsError(f"run already exists: {path}")
    path.write_text(
        yaml.safe_dump(run.to_mapping(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def load_run(path: Path) -> Run:
    """Load one run record without changing it."""
    try:
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RunValidationError(f"invalid YAML in {path}: {error}") from error
    if not isinstance(record, dict):
        raise RunValidationError("run record must be a YAML mapping")
    return Run.from_mapping(record)


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise RunValidationError(
            f"{field} must use lowercase letters, digits, and underscores, starting with a letter"
        )
    return value


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RunValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise RunValidationError(f"{field} must be an ISO-8601 timestamp")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise RunValidationError(f"{field} must be an ISO-8601 timestamp") from error
    if timestamp.tzinfo is None:
        raise RunValidationError(f"{field} must include a timezone")
    return timestamp
