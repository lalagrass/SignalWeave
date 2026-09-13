"""Validated private mapping import with explicit rollback reporting."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from signalweave.basket import BasketValidationError, load_basket
from signalweave.identifier_mapping import (
    IdentifierMapping,
    IdentifierMappingError,
    METHOD_VERSION,
    validate_identifier_mapping_write,
    write_identifier_mapping,
)
from signalweave.runs import RunValidationError, create_run, load_run, write_run
from signalweave.schema import IDENTIFIER


SCHEMA_VERSION = 1
ROOT_FIELDS = frozenset(
    {"schema_version", "mapping_id", "supersedes_mapping_id", "provenance", "members"}
)
PROVENANCE_FIELDS = frozenset(
    {"provider", "model_id", "model_locality", "drafted_by", "method_version", "created_at"}
)


class IdentifierMappingImportError(ValueError):
    """Raised when a mapping bundle cannot be safely imported."""


class IdentifierMappingRollbackError(IdentifierMappingImportError):
    """Raised when a failed import could not remove every new private record."""


@dataclass(frozen=True)
class MappingBundleProvenance:
    provider: str
    model_id: str
    model_locality: str
    drafted_by: str
    created_at: datetime


@dataclass(frozen=True)
class IdentifierMappingBundle:
    mapping_id: str
    supersedes_mapping_id: str | None
    provenance: MappingBundleProvenance
    members: tuple[dict[str, Any], ...]
    canonical_json: str


@dataclass(frozen=True)
class IdentifierMappingImportResult:
    run_path: Path
    mapping_path: Path


def load_identifier_mapping_bundle(path: Path) -> IdentifierMappingBundle:
    """Load a strict JSON bundle without echoing private member values."""
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IdentifierMappingImportError("identifier mapping bundle must be valid JSON") from error
    if not isinstance(record, dict):
        raise IdentifierMappingImportError("identifier mapping bundle must be a JSON object")
    _exact_fields(record, ROOT_FIELDS, "identifier mapping bundle")
    if type(record["schema_version"]) is not int or record["schema_version"] != SCHEMA_VERSION:
        raise IdentifierMappingImportError("identifier mapping bundle must use schema_version 1")
    mapping_id = _identifier(record["mapping_id"], "mapping_id")
    supersedes = record["supersedes_mapping_id"]
    if supersedes is not None:
        supersedes = _identifier(supersedes, "supersedes_mapping_id")
    provenance = _provenance(record["provenance"])
    members = record["members"]
    if not isinstance(members, list):
        raise IdentifierMappingImportError("identifier mapping bundle members must be a list")
    return IdentifierMappingBundle(
        mapping_id=mapping_id,
        supersedes_mapping_id=supersedes,
        provenance=provenance,
        members=tuple(members),
        canonical_json=json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


def import_identifier_mapping(
    bundle_path: Path,
    *,
    thread_id: str,
    workspace_root: Path,
) -> IdentifierMappingImportResult:
    """Validate the basket, run, and sidecar before writing both records."""
    root, threads_directory, runs_directory, mappings_directory = _private_directories(
        workspace_root
    )
    _require_private_bundle_path(bundle_path, root)
    bundle = load_identifier_mapping_bundle(bundle_path)
    if not isinstance(thread_id, str) or not IDENTIFIER.fullmatch(thread_id):
        raise IdentifierMappingImportError("thread must be a lowercase identifier")
    try:
        basket = load_basket(threads_directory / thread_id)
        basket_run = load_run(runs_directory / f"{basket.run_id}.yaml")
    except (
        BasketValidationError,
        RunValidationError,
        OSError,
        UnicodeDecodeError,
        ValueError,
    ) as error:
        raise IdentifierMappingImportError("bound basket snapshot is unavailable") from error
    if basket.thread_id != thread_id or basket_run.run_id != basket.run_id:
        raise IdentifierMappingImportError("bound basket snapshot identity is inconsistent")

    run = create_run(
        provider=bundle.provenance.provider,
        model_id=bundle.provenance.model_id,
        model_locality=bundle.provenance.model_locality,
        method_version=METHOD_VERSION,
        input_id=f"{basket.thread_id}:{basket.run_id}",
        output=bundle.canonical_json,
        created_at=bundle.provenance.created_at,
    )
    try:
        mapping = IdentifierMapping.from_mapping(
            {
                "schema_version": SCHEMA_VERSION,
                "mapping_id": bundle.mapping_id,
                "supersedes_mapping_id": bundle.supersedes_mapping_id,
                "thread_id": basket.thread_id,
                "basket_run_id": basket.run_id,
                "basket_created_at": basket.created_at.isoformat(),
                "members": list(bundle.members),
                "provenance": {
                    "review_status": "unreviewed",
                    "drafted_by": bundle.provenance.drafted_by,
                    "run_id": run.run_id,
                    "provider": run.provider,
                    "model_id": run.model_id,
                    "model_locality": run.model_locality,
                    "method_version": run.method_version,
                    "created_at": run.created_at.isoformat(),
                },
            }
        )
    except IdentifierMappingError as error:
        raise IdentifierMappingImportError("identifier mapping bundle is invalid") from error
    if tuple(member.declared_identifier for member in mapping.members) != basket.instruments:
        raise IdentifierMappingImportError(
            "identifier mapping members must exactly match the bound basket"
        )
    if mapping.provenance.created_at < basket.created_at:
        raise IdentifierMappingImportError("identifier mapping must not predate its basket")

    run_path = runs_directory / f"{run.run_id}.yaml"
    mapping_path = mappings_directory / f"{mapping.mapping_id}.yaml"
    with _mapping_import_lock(mappings_directory):
        try:
            validate_identifier_mapping_write(mapping, mappings_directory)
        except (FileExistsError, IdentifierMappingError) as error:
            raise IdentifierMappingImportError("identifier mapping revision cannot be appended") from error
        if run_path.exists() or mapping_path.exists():
            raise IdentifierMappingImportError("identifier mapping import collides with private records")
        try:
            write_run(run, runs_directory)
            write_identifier_mapping(mapping, mappings_directory)
        except (OSError, FileExistsError, IdentifierMappingError) as error:
            rollback_failures = _remove_new_paths(mapping_path, run_path)
            if rollback_failures:
                raise IdentifierMappingRollbackError(
                    "identifier mapping import failed and rollback is incomplete"
                ) from error
            raise IdentifierMappingImportError(
                "identifier mapping import could not complete; no records were retained"
            ) from error
    return IdentifierMappingImportResult(run_path=run_path, mapping_path=mapping_path)


def _provenance(value: Any) -> MappingBundleProvenance:
    if not isinstance(value, dict):
        raise IdentifierMappingImportError("mapping provenance must be a JSON object")
    _exact_fields(value, PROVENANCE_FIELDS, "mapping provenance")
    if value["method_version"] != METHOD_VERSION:
        raise IdentifierMappingImportError(
            "mapping provenance must use method_version identifier_mapping_v1"
        )
    provider = _identifier(value["provider"], "provider")
    drafted_by = _identifier(value["drafted_by"], "drafted_by")
    if not isinstance(value["model_id"], str) or not value["model_id"].strip():
        raise IdentifierMappingImportError("model_id must be a non-empty string")
    if value["model_locality"] not in {"local", "remote"}:
        raise IdentifierMappingImportError("model_locality must be local or remote")
    if not isinstance(value["created_at"], str):
        raise IdentifierMappingImportError("created_at must be an ISO-8601 timestamp")
    try:
        created_at = datetime.fromisoformat(value["created_at"])
    except ValueError as error:
        raise IdentifierMappingImportError("created_at must be an ISO-8601 timestamp") from error
    if created_at.tzinfo is None:
        raise IdentifierMappingImportError("created_at must include a timezone")
    return MappingBundleProvenance(
        provider=provider,
        model_id=value["model_id"].strip(),
        model_locality=value["model_locality"],
        drafted_by=drafted_by,
        created_at=created_at,
    )


def _private_directories(workspace_root: Path) -> tuple[Path, Path, Path, Path]:
    root = workspace_root.resolve()
    try:
        result = subprocess.run(
            ("git", "-C", str(root), "rev-parse", "--show-toplevel"),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise IdentifierMappingImportError("mapping import requires a Git workspace root") from error
    if result.returncode != 0 or not result.stdout.strip() or Path(result.stdout.strip()).resolve() != root:
        raise IdentifierMappingImportError("mapping import requires the Git workspace top-level")
    directories = (
        root / "data" / "private" / "threads",
        root / "data" / "private" / "runs",
        root / "data" / "private" / "identifier-mappings",
    )
    for directory in directories:
        resolved = directory.resolve()
        if resolved != directory:
            raise IdentifierMappingImportError("mapping outputs must use exact private workspace roots")
        relative_probe = resolved.relative_to(root) / ".identifier_mapping_probe"
        ignored = subprocess.run(
            ("git", "-C", str(root), "check-ignore", "-q", "--no-index", str(relative_probe)),
            check=False,
            capture_output=True,
            text=True,
        )
        if ignored.returncode != 0:
            raise IdentifierMappingImportError("mapping outputs must use Git-ignored private zones")
    return root, *directories


def _require_private_bundle_path(bundle_path: Path, root: Path) -> None:
    try:
        relative = bundle_path.resolve().relative_to(root)
    except ValueError as error:
        raise IdentifierMappingImportError(
            "identifier mapping bundle must remain inside the private workspace"
        ) from error
    if relative.parts[:2] != ("data", "private"):
        raise IdentifierMappingImportError(
            "identifier mapping bundle must remain inside the private workspace"
        )
    ignored = subprocess.run(
        ("git", "-C", str(root), "check-ignore", "-q", "--no-index", str(relative)),
        check=False,
        capture_output=True,
        text=True,
    )
    if ignored.returncode != 0:
        raise IdentifierMappingImportError("identifier mapping bundle must be Git-ignored")
    tracked = subprocess.run(
        ("git", "-C", str(root), "ls-files", "--error-unmatch", "--", str(relative)),
        check=False,
        capture_output=True,
        text=True,
    )
    if tracked.returncode == 0:
        raise IdentifierMappingImportError("identifier mapping bundle must not be tracked")


@contextmanager
def _mapping_import_lock(mappings_directory: Path):
    mappings_directory.mkdir(parents=True, exist_ok=True)
    lock_path = mappings_directory / ".identifier_mapping_import.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise IdentifierMappingImportError(
                "another identifier mapping import is already in progress"
            ) from error
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _remove_new_paths(*paths: Path) -> tuple[Path, ...]:
    failures: list[Path] = []
    for path in paths:
        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
        except OSError:
            failures.append(path)
    return tuple(failures)


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise IdentifierMappingImportError(f"{field} must be a lowercase identifier")
    return value


def _exact_fields(record: dict[str, Any], fields: frozenset[str], label: str) -> None:
    if record.keys() != fields:
        raise IdentifierMappingImportError(f"{label} has invalid fields")
