from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from signalweave.basket import Basket, BasketValidationError, create_basket
from signalweave.identifier_mapping import (
    IdentifierMapping,
    IdentifierMappingError,
    load_active_identifier_mapping,
    mapping_provenance,
    write_identifier_mapping,
)
from signalweave.runs import create_run, write_run


CREATED_AT = datetime(2026, 9, 11, tzinfo=timezone.utc)


def _basket() -> Basket:
    return create_basket(
        thread_id="story_synthetic_001",
        instruments=["synthetic_one", "synthetic_two"],
        drafted_by="model_synthetic",
        run_id="run_basket_synthetic001",
        created_at=CREATED_AT,
    )


def _mapping(mapping_id: str, *, supersedes: str | None = None, basket: Basket | None = None) -> IdentifierMapping:
    basket = basket or _basket()
    return IdentifierMapping.from_mapping(
        {
            "schema_version": 1,
            "mapping_id": mapping_id,
            "supersedes_mapping_id": supersedes,
            "thread_id": basket.thread_id,
            "basket_run_id": basket.run_id,
            "basket_created_at": basket.created_at.isoformat(),
            "members": [
                {"declared_identifier": "synthetic_one", "mapping_status": "resolved", "venue": "TWSE", "symbol": "1234", "reason": None},
                {"declared_identifier": "synthetic_two", "mapping_status": "unresolved", "venue": None, "symbol": None, "reason": "No canonical listing supplied."},
            ],
            "provenance": {
                "review_status": "unreviewed",
                "drafted_by": "mapping_agent_synthetic",
                "run_id": "run_mapping_synthetic001",
                "provider": "synthetic_provider",
                "model_id": "synthetic-mapper",
                "model_locality": "local",
                "method_version": "identifier_mapping_v1",
                "created_at": CREATED_AT.isoformat(),
            },
        }
    )


def test_new_basket_rejects_duplicate_members() -> None:
    with pytest.raises(BasketValidationError, match="duplicates"):
        _basket().from_mapping(
            {
                "thread_id": "story_synthetic_001",
                "instruments": ["synthetic_one", "synthetic_one"],
                "review_status": "unreviewed",
                "drafted_by": "model_synthetic",
                "run_id": "run_basket_synthetic001",
                "created_at": CREATED_AT.isoformat(),
            }
        )


def test_mapping_requires_exact_basket_binding_and_member_order(tmp_path: Path) -> None:
    basket = _basket()
    directory = tmp_path / "identifier-mappings"
    mapping = _mapping("mapping_synthetic001", basket=basket)
    write_identifier_mapping(mapping, directory)

    assert load_active_identifier_mapping(directory, basket=basket) == mapping

    wrong_snapshot = create_basket(
        thread_id=basket.thread_id,
        instruments=list(basket.instruments),
        drafted_by=basket.drafted_by,
        run_id="run_basket_other",
        created_at=basket.created_at,
    )
    with pytest.raises(IdentifierMappingError, match="no active"):
        load_active_identifier_mapping(directory, basket=wrong_snapshot)


def test_mapping_rejects_duplicate_or_reordered_members() -> None:
    record = _mapping("mapping_synthetic001").to_mapping()
    record["members"] = [record["members"][0], record["members"][0]]
    with pytest.raises(IdentifierMappingError, match="must not repeat"):
        IdentifierMapping.from_mapping(record)


def test_mapping_correction_is_immutable_and_requires_exact_supersession(tmp_path: Path) -> None:
    directory = tmp_path / "identifier-mappings"
    first = _mapping("mapping_synthetic001")
    write_identifier_mapping(first, directory)
    corrected = _mapping("mapping_synthetic002", supersedes=first.mapping_id)
    write_identifier_mapping(corrected, directory)

    assert load_active_identifier_mapping(directory, basket=_basket()).mapping_id == corrected.mapping_id
    with pytest.raises(IdentifierMappingError, match="must supersede"):
        write_identifier_mapping(_mapping("mapping_synthetic003"), directory)
    with pytest.raises(FileExistsError, match="already exists"):
        write_identifier_mapping(corrected, directory)


def test_mapping_rejects_multiple_active_revisions_for_one_snapshot(tmp_path: Path) -> None:
    directory = tmp_path / "identifier-mappings"
    first = _mapping("mapping_synthetic001")
    write_identifier_mapping(first, directory)
    conflicting = _mapping("mapping_synthetic002")
    # Simulate a manually-created conflicting sidecar; the loader must refuse
    # rather than choosing by file name or time.
    (directory / "mapping_synthetic002.yaml").write_text(
        yaml.safe_dump(conflicting.to_mapping(), sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(IdentifierMappingError, match="multiple active"):
        load_active_identifier_mapping(directory, basket=_basket())


def test_mapping_rejects_cross_snapshot_supersession_even_if_written_manually(tmp_path: Path) -> None:
    directory = tmp_path / "identifier-mappings"
    first = _mapping("mapping_synthetic001")
    write_identifier_mapping(first, directory)
    other_basket = create_basket(
        thread_id="story_other_001",
        instruments=["synthetic_one", "synthetic_two"],
        drafted_by="model_synthetic",
        run_id="run_basket_other001",
        created_at=CREATED_AT,
    )
    invalid = _mapping("mapping_synthetic002", supersedes=first.mapping_id, basket=other_basket)
    (directory / "mapping_synthetic002.yaml").write_text(
        yaml.safe_dump(invalid.to_mapping(), sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(IdentifierMappingError, match="same basket snapshot"):
        load_active_identifier_mapping(directory, basket=_basket())


def test_mapping_provenance_must_match_its_independent_run(tmp_path: Path) -> None:
    mapping = _mapping("mapping_synthetic001")
    runs = tmp_path / "runs"
    write_run(
        create_run(
            provider="other_provider",
            model_id="synthetic-mapper",
            model_locality="local",
            method_version="identifier_mapping_v1",
            input_id="synthetic_input",
            output="{}",
            run_id="run_mapping_synthetic001",
            created_at=CREATED_AT,
        ),
        runs,
    )

    with pytest.raises(IdentifierMappingError, match="disagrees"):
        mapping_provenance(mapping, runs)


@pytest.mark.parametrize(
    "status, venue, symbol, reason, message",
    [
        ("resolved", None, None, None, "canonical venue"),
        ("unresolved", "TWSE", "1234", "reason", "must be null"),
        ("unresolved", None, None, None, "non-empty string"),
        ("not_publicly_listed", "TWSE", "1234", None, "must be null"),
    ],
)
def test_mapping_status_invariants(status, venue, symbol, reason, message) -> None:
    record = _mapping("mapping_synthetic001").to_mapping()
    record["members"][0] = {
        "declared_identifier": "synthetic_one",
        "mapping_status": status,
        "venue": venue,
        "symbol": symbol,
        "reason": reason,
    }
    with pytest.raises(IdentifierMappingError, match=message):
        IdentifierMapping.from_mapping(record)
