"""Immutable private identity mappings for one exact basket snapshot.

An identifier mapping is deliberately separate from a basket: it can correct
the canonical identity of a declared member without pretending that the
original basket was authored differently.  Mapping records are private input
to export v2, never a price or listing-data lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Any

import yaml

from signalweave.basket import Basket
from signalweave.runs import Run, load_run
from signalweave.schema import IDENTIFIER


SCHEMA_VERSION = 1
METHOD_VERSION = "identifier_mapping_v1"
STATUSES = frozenset({"resolved", "unresolved", "not_publicly_listed"})
VENUE = re.compile(r"^[A-Z][A-Z0-9._-]*$")
SYMBOL = re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$")
ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "mapping_id",
        "supersedes_mapping_id",
        "thread_id",
        "basket_run_id",
        "basket_created_at",
        "members",
        "provenance",
    }
)
MEMBER_FIELDS = frozenset(
    {"declared_identifier", "mapping_status", "venue", "symbol", "reason"}
)
PROVENANCE_FIELDS = frozenset(
    {
        "review_status",
        "drafted_by",
        "run_id",
        "provider",
        "model_id",
        "model_locality",
        "method_version",
        "created_at",
    }
)


class IdentifierMappingError(ValueError):
    """Raised when an identity mapping is not a complete snapshot binding."""


@dataclass(frozen=True)
class MappingProvenance:
    review_status: str
    drafted_by: str
    run_id: str
    provider: str
    model_id: str
    model_locality: str
    method_version: str
    created_at: datetime

    def to_mapping(self) -> dict[str, str]:
        return {
            "review_status": self.review_status,
            "drafted_by": self.drafted_by,
            "run_id": self.run_id,
            "provider": self.provider,
            "model_id": self.model_id,
            "model_locality": self.model_locality,
            "method_version": self.method_version,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class IdentifierMember:
    declared_identifier: str
    mapping_status: str
    venue: str | None
    symbol: str | None
    reason: str | None

    def to_mapping(self) -> dict[str, str | None]:
        return {
            "declared_identifier": self.declared_identifier,
            "mapping_status": self.mapping_status,
            "venue": self.venue,
            "symbol": self.symbol,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class IdentifierMapping:
    mapping_id: str
    supersedes_mapping_id: str | None
    thread_id: str
    basket_run_id: str
    basket_created_at: datetime
    members: tuple[IdentifierMember, ...]
    provenance: MappingProvenance

    @classmethod
    def from_mapping(cls, record: dict[str, Any]) -> "IdentifierMapping":
        _exact_fields(record, ROOT_FIELDS, "identifier mapping")
        if type(record["schema_version"]) is not int or record["schema_version"] != SCHEMA_VERSION:
            raise IdentifierMappingError("identifier mapping must use schema_version 1")
        supersedes = record["supersedes_mapping_id"]
        if supersedes is not None:
            supersedes = _identifier(supersedes, "supersedes_mapping_id")
        members_value = record["members"]
        if not isinstance(members_value, list):
            raise IdentifierMappingError("members must be a list")
        members = tuple(_member(value) for value in members_value)
        declared = tuple(member.declared_identifier for member in members)
        if len(set(declared)) != len(declared):
            raise IdentifierMappingError("members must not repeat declared_identifier")
        return cls(
            mapping_id=_identifier(record["mapping_id"], "mapping_id"),
            supersedes_mapping_id=supersedes,
            thread_id=_identifier(record["thread_id"], "thread_id"),
            basket_run_id=_identifier(record["basket_run_id"], "basket_run_id"),
            basket_created_at=_timestamp(record["basket_created_at"], "basket_created_at"),
            members=members,
            provenance=_provenance(record["provenance"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "mapping_id": self.mapping_id,
            "supersedes_mapping_id": self.supersedes_mapping_id,
            "thread_id": self.thread_id,
            "basket_run_id": self.basket_run_id,
            "basket_created_at": self.basket_created_at.isoformat(),
            "members": [member.to_mapping() for member in self.members],
            "provenance": self.provenance.to_mapping(),
        }


def write_identifier_mapping(mapping: IdentifierMapping, directory: Path) -> Path:
    """Write one mapping revision, refusing overwrite or ambiguous active state."""
    directory.mkdir(parents=True, exist_ok=True)
    validate_identifier_mapping_write(mapping, directory)
    path = directory / f"{mapping.mapping_id}.yaml"
    path.write_text(
        yaml.safe_dump(mapping.to_mapping(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def validate_identifier_mapping_write(mapping: IdentifierMapping, directory: Path) -> None:
    """Preflight one append-only revision without writing private state."""
    existing = _load_directory(directory)
    if any(item.mapping_id == mapping.mapping_id for item in existing):
        raise FileExistsError(f"identifier mapping already exists: {mapping.mapping_id}")
    same_snapshot = [item for item in existing if _same_snapshot(item, mapping)]
    active = _active(same_snapshot)
    if len(active) > 1:
        raise IdentifierMappingError("identifier mapping snapshot has multiple active revisions")
    if not same_snapshot and mapping.supersedes_mapping_id is not None:
        raise IdentifierMappingError("identifier mapping cannot supersede an unknown snapshot")
    if same_snapshot:
        if len(active) != 1 or mapping.supersedes_mapping_id != active[0].mapping_id:
            raise IdentifierMappingError("identifier mapping revision must supersede the one active mapping")
        if mapping.provenance.created_at < active[0].provenance.created_at:
            raise IdentifierMappingError("identifier mapping revision must not predate its predecessor")


def load_active_identifier_mapping(
    directory: Path, *, basket: Basket
) -> IdentifierMapping:
    """Load the one active mapping that binds exactly to ``basket``."""
    candidates = [
        mapping
        for mapping in _load_directory(directory)
        if mapping.thread_id == basket.thread_id
        and mapping.basket_run_id == basket.run_id
        and mapping.basket_created_at == basket.created_at
    ]
    active = _active(candidates)
    if not active:
        raise IdentifierMappingError("no active identifier mapping for this basket snapshot")
    if len(active) != 1:
        raise IdentifierMappingError("identifier mapping snapshot has multiple active revisions")
    mapping = active[0]
    if tuple(member.declared_identifier for member in mapping.members) != basket.instruments:
        raise IdentifierMappingError("identifier mapping members must exactly match the bound basket")
    return mapping


def mapping_provenance(mapping: IdentifierMapping, runs_directory: Path) -> MappingProvenance:
    """Verify that independently declared mapping provenance matches its run."""
    try:
        run = load_run(runs_directory / f"{mapping.provenance.run_id}.yaml")
    except (OSError, ValueError) as error:
        raise IdentifierMappingError("identifier mapping provenance run is unavailable") from error
    _matches_run(mapping.provenance, run)
    return mapping.provenance


def _load_directory(directory: Path) -> list[IdentifierMapping]:
    if not directory.is_dir():
        return []
    mappings: list[IdentifierMapping] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
            raise IdentifierMappingError("identifier mapping must be valid YAML") from error
        if not isinstance(record, dict):
            raise IdentifierMappingError("identifier mapping must be a YAML mapping")
        mappings.append(IdentifierMapping.from_mapping(record))
    by_id = {mapping.mapping_id: mapping for mapping in mappings}
    if len(by_id) != len(mappings):
        raise IdentifierMappingError("identifier mapping ids must be unique")
    for mapping in mappings:
        if mapping.supersedes_mapping_id is None:
            continue
        superseded = by_id.get(mapping.supersedes_mapping_id)
        if superseded is None:
            raise IdentifierMappingError("identifier mapping supersedes an unknown mapping")
        if not _same_snapshot(mapping, superseded):
            raise IdentifierMappingError("identifier mapping supersession must keep the same basket snapshot")
    return mappings


def _active(mappings: list[IdentifierMapping]) -> list[IdentifierMapping]:
    superseded = {item.supersedes_mapping_id for item in mappings if item.supersedes_mapping_id}
    return [item for item in mappings if item.mapping_id not in superseded]


def _same_snapshot(left: IdentifierMapping, right: IdentifierMapping) -> bool:
    return (
        left.thread_id == right.thread_id
        and left.basket_run_id == right.basket_run_id
        and left.basket_created_at == right.basket_created_at
    )


def _member(value: Any) -> IdentifierMember:
    _exact_fields(value, MEMBER_FIELDS, "identifier mapping member")
    status = value["mapping_status"]
    if status not in STATUSES:
        raise IdentifierMappingError("mapping_status must be resolved, unresolved, or not_publicly_listed")
    venue = value["venue"]
    symbol = value["symbol"]
    reason = value["reason"]
    if status == "resolved":
        if not isinstance(venue, str) or not VENUE.fullmatch(venue):
            raise IdentifierMappingError("resolved mapping venue must be a canonical venue")
        if not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol):
            raise IdentifierMappingError("resolved mapping symbol must be a canonical symbol")
        if reason is not None:
            raise IdentifierMappingError("resolved mapping reason must be null")
    elif status == "unresolved":
        if venue is not None or symbol is not None:
            raise IdentifierMappingError("unresolved mapping venue and symbol must be null")
        if not isinstance(reason, str) or not reason.strip():
            raise IdentifierMappingError("unresolved mapping reason must be a non-empty string")
    else:
        if venue is not None or symbol is not None:
            raise IdentifierMappingError("not_publicly_listed venue and symbol must be null")
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            raise IdentifierMappingError("not_publicly_listed reason must be null or a non-empty string")
    return IdentifierMember(
        declared_identifier=_instrument(value["declared_identifier"]),
        mapping_status=status,
        venue=venue,
        symbol=symbol,
        reason=reason.strip() if isinstance(reason, str) else None,
    )


def _provenance(value: Any) -> MappingProvenance:
    _exact_fields(value, PROVENANCE_FIELDS, "identifier mapping provenance")
    if value["review_status"] != "unreviewed":
        raise IdentifierMappingError("identifier mapping review_status must be 'unreviewed'")
    if value["model_locality"] not in {"local", "remote"}:
        raise IdentifierMappingError("identifier mapping model_locality must be local or remote")
    if value["method_version"] != METHOD_VERSION:
        raise IdentifierMappingError(
            "identifier mapping method_version must be identifier_mapping_v1"
        )
    return MappingProvenance(
        review_status="unreviewed",
        drafted_by=_identifier(value["drafted_by"], "mapping drafted_by"),
        run_id=_identifier(value["run_id"], "mapping run_id"),
        provider=_identifier(value["provider"], "mapping provider"),
        model_id=_non_empty_string(value["model_id"], "mapping model_id"),
        model_locality=value["model_locality"],
        method_version=METHOD_VERSION,
        created_at=_timestamp(value["created_at"], "mapping created_at"),
    )


def _matches_run(provenance: MappingProvenance, run: Run) -> None:
    if (
        provenance.provider != run.provider
        or provenance.model_id != run.model_id
        or provenance.model_locality != run.model_locality
        or provenance.method_version != run.method_version
        or provenance.created_at != run.created_at
    ):
        raise IdentifierMappingError("identifier mapping provenance disagrees with its run")


def _exact_fields(value: Any, fields: frozenset[str], label: str) -> None:
    if not isinstance(value, dict) or value.keys() != fields:
        raise IdentifierMappingError(f"{label} has invalid fields")


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise IdentifierMappingError(f"{field} must be a lowercase identifier")
    return value


def _instrument(value: Any) -> str:
    if not isinstance(value, str) or not SYMBOL.fullmatch(value):
        raise IdentifierMappingError("declared_identifier must be a basket instrument")
    return value


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IdentifierMappingError(f"{field} must be a non-empty string")
    return value.strip()


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise IdentifierMappingError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise IdentifierMappingError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise IdentifierMappingError(f"{field} must include a timezone")
    return parsed
