from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import pytest
import yaml

import signalweave.cli as cli_module
import signalweave.identifier_mapping_import as import_module
from signalweave.basket import create_basket, load_basket, write_basket
from signalweave.identifier_mapping import METHOD_VERSION, load_active_identifier_mapping
from signalweave.identifier_mapping_import import (
    IdentifierMappingImportError,
    IdentifierMappingRollbackError,
    import_identifier_mapping,
    load_identifier_mapping_bundle,
)
from signalweave.cli import main
from signalweave.runs import create_run, load_run, write_run
from signalweave.threads import create_thread, write_thread


FIXTURE = Path(__file__).parent / "fixtures" / "identifier-mapping-bundle-v1.json"
CREATED_AT = datetime(2026, 9, 13, tzinfo=timezone.utc)


def _initialize_repository(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".gitignore").write_text("data/private/\n", encoding="utf-8")


def _workspace(tmp_path: Path) -> Path:
    _initialize_repository(tmp_path)
    runs = tmp_path / "data" / "private" / "runs"
    source_run = create_run(
        provider="openai",
        model_id="gpt-synthetic-1",
        model_locality="remote",
        method_version="basket_v2",
        input_id="story_synthetic_001",
        output='{"instruments":["synthetic_one","synthetic_two"]}',
        run_id="run_basket_synthetic001",
        created_at=CREATED_AT,
    )
    write_run(source_run, runs)
    thread = create_thread(
        thread_id="story_synthetic_001",
        mechanism="Synthetic mechanism.",
        open_question="Synthetic question?",
        invalidation_conditions=["Synthetic invalidation."],
        groups=["synthetic group"],
        market_sentiment="Synthetic sentiment.",
        review_date="2026-09-27",
        created_by="agent_synthetic",
        drafted_by="agent_synthetic",
        run_id=source_run.run_id,
        created_at=CREATED_AT,
    )
    write_thread(thread, tmp_path / "data" / "private" / "threads")
    basket = create_basket(
        thread_id="story_synthetic_001",
        instruments=["synthetic_one", "synthetic_two"],
        drafted_by="agent_synthetic",
        run_id=source_run.run_id,
        created_at=CREATED_AT,
    )
    write_basket(basket, tmp_path / "data" / "private" / "threads")
    return tmp_path


def _bundle(tmp_path: Path, mutate=None) -> Path:
    record = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(record)
    path = tmp_path / "data" / "private" / "worklog" / "mapping-bundle.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_import_creates_matching_run_and_snapshot_bound_mapping(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = import_identifier_mapping(
        _bundle(tmp_path), thread_id="story_synthetic_001", workspace_root=root
    )

    run = load_run(result.run_path)
    basket = load_basket(root / "data" / "private" / "threads" / "story_synthetic_001")
    mapping = load_active_identifier_mapping(
        root / "data" / "private" / "identifier-mappings", basket=basket
    )

    assert run.method_version == "identifier_mapping_v1"
    assert run.provider == "openai"
    assert mapping.provenance.run_id == run.run_id
    assert mapping.provenance.method_version == run.method_version
    assert mapping.thread_id == basket.thread_id
    assert mapping.basket_run_id == basket.run_id
    assert mapping.basket_created_at == basket.created_at


def test_wrong_method_is_rejected_before_writes(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    bundle = _bundle(
        tmp_path,
        lambda record: record["provenance"].update({"method_version": "basket_v2"}),
    )

    with pytest.raises(IdentifierMappingImportError, match="identifier_mapping_v1"):
        import_identifier_mapping(bundle, thread_id="story_synthetic_001", workspace_root=root)

    assert not (root / "data" / "private" / "identifier-mappings").exists()
    assert len(list((root / "data" / "private" / "runs").glob("*.yaml"))) == 1


def test_member_order_mismatch_is_rejected_without_partial_run(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    bundle = _bundle(tmp_path, lambda record: record["members"].reverse())

    with pytest.raises(IdentifierMappingImportError, match="exactly match"):
        import_identifier_mapping(bundle, thread_id="story_synthetic_001", workspace_root=root)

    assert not (root / "data" / "private" / "identifier-mappings").exists()
    assert len(list((root / "data" / "private" / "runs").glob("*.yaml"))) == 1


def test_missing_basket_run_is_rejected_before_mapping_write(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    (root / "data" / "private" / "runs" / "run_basket_synthetic001.yaml").unlink()

    with pytest.raises(IdentifierMappingImportError, match="snapshot is unavailable"):
        import_identifier_mapping(
            _bundle(tmp_path), thread_id="story_synthetic_001", workspace_root=root
        )

    assert not (root / "data" / "private" / "identifier-mappings").exists()


@pytest.mark.parametrize("mismatch", ["basket", "run"])
def test_snapshot_internal_identity_mismatch_is_rejected(
    tmp_path: Path, mismatch: str
) -> None:
    root = _workspace(tmp_path)
    if mismatch == "basket":
        path = root / "data" / "private" / "threads" / "story_synthetic_001" / "basket.yaml"
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        record["thread_id"] = "story_other_001"
    else:
        path = root / "data" / "private" / "runs" / "run_basket_synthetic001.yaml"
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        record["run_id"] = "run_basket_other001"
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    with pytest.raises(IdentifierMappingImportError, match="identity is inconsistent"):
        import_identifier_mapping(
            _bundle(tmp_path), thread_id="story_synthetic_001", workspace_root=root
        )

    assert not (root / "data" / "private" / "identifier-mappings").exists()


def test_mapping_must_not_predate_its_basket(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    bundle = _bundle(
        tmp_path,
        lambda record: record["provenance"].update(
            {"created_at": "2026-09-12T23:59:59+00:00"}
        ),
    )

    with pytest.raises(IdentifierMappingImportError, match="must not predate"):
        import_identifier_mapping(bundle, thread_id="story_synthetic_001", workspace_root=root)


def test_failed_mapping_write_removes_new_run_and_sidecar(
    tmp_path: Path, monkeypatch
) -> None:
    root = _workspace(tmp_path)
    original_write = import_module.write_identifier_mapping

    def write_then_fail(mapping, directory):
        original_write(mapping, directory)
        raise OSError("synthetic write failure")

    monkeypatch.setattr(import_module, "write_identifier_mapping", write_then_fail)
    with pytest.raises(IdentifierMappingImportError, match="no records were retained"):
        import_identifier_mapping(
            _bundle(tmp_path), thread_id="story_synthetic_001", workspace_root=root
        )

    assert not list((root / "data" / "private" / "identifier-mappings").glob("*.yaml"))
    assert len(list((root / "data" / "private" / "runs").glob("*.yaml"))) == 1


def test_incomplete_rollback_is_reported_without_a_false_no_records_claim(
    tmp_path: Path, monkeypatch
) -> None:
    root = _workspace(tmp_path)
    original_write = import_module.write_identifier_mapping
    original_unlink = Path.unlink

    def write_then_fail(mapping, directory):
        original_write(mapping, directory)
        raise OSError("synthetic write failure")

    def refuse_run_cleanup(path, *args, **kwargs):
        if path.parent.name == "runs" and path.name != "run_basket_synthetic001.yaml":
            raise OSError("synthetic cleanup failure")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(import_module, "write_identifier_mapping", write_then_fail)
    monkeypatch.setattr(Path, "unlink", refuse_run_cleanup)

    with pytest.raises(IdentifierMappingRollbackError, match="rollback is incomplete"):
        import_identifier_mapping(
            _bundle(tmp_path), thread_id="story_synthetic_001", workspace_root=root
        )

    assert not list((root / "data" / "private" / "identifier-mappings").glob("*.yaml"))
    assert len(list((root / "data" / "private" / "runs").glob("*.yaml"))) == 2


def test_revision_must_explicitly_supersede_active_mapping(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    import_identifier_mapping(
        _bundle(tmp_path), thread_id="story_synthetic_001", workspace_root=root
    )

    def correction(record):
        record["mapping_id"] = "mapping_synthetic002"
        record["supersedes_mapping_id"] = "mapping_synthetic001"

    result = import_identifier_mapping(
        _bundle(tmp_path, correction),
        thread_id="story_synthetic_001",
        workspace_root=root,
    )
    assert result.mapping_path.name == "mapping_synthetic002.yaml"

    def ambiguous(record):
        record["mapping_id"] = "mapping_synthetic003"

    with pytest.raises(IdentifierMappingImportError, match="cannot be appended"):
        import_identifier_mapping(
            _bundle(tmp_path, ambiguous),
            thread_id="story_synthetic_001",
            workspace_root=root,
        )


def test_bundle_loader_rejects_unknown_fields_without_echoing_values(tmp_path: Path) -> None:
    private_value = "source_specific_synthetic_value"
    bundle = _bundle(tmp_path, lambda record: record.update({"unexpected": private_value}))

    with pytest.raises(IdentifierMappingImportError) as caught:
        load_identifier_mapping_bundle(bundle)

    assert private_value not in str(caught.value)


def test_importer_rejects_non_root_workspace(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    nested = root / "nested"
    nested.mkdir()

    with pytest.raises(IdentifierMappingImportError, match="Git workspace top-level"):
        import_identifier_mapping(
            _bundle(tmp_path), thread_id="story_synthetic_001", workspace_root=nested
        )


def test_importer_rejects_bundle_outside_ignored_private_zone(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    public_bundle = root / "mapping-bundle.json"
    public_bundle.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(IdentifierMappingImportError, match="private workspace"):
        import_identifier_mapping(
            public_bundle, thread_id="story_synthetic_001", workspace_root=root
        )

    assert not (root / "data" / "private" / "identifier-mappings").exists()
    assert len(list((root / "data" / "private" / "runs").glob("*.yaml"))) == 1


def test_importer_rejects_force_tracked_private_bundle(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    bundle = _bundle(tmp_path)
    subprocess.run(["git", "add", "-f", str(bundle.relative_to(root))], cwd=root, check=True)

    with pytest.raises(IdentifierMappingImportError, match="must not be tracked"):
        import_identifier_mapping(bundle, thread_id="story_synthetic_001", workspace_root=root)

    assert not (root / "data" / "private" / "identifier-mappings").exists()


def test_cli_import_reports_only_safe_counts(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _workspace(tmp_path)
    bundle = _bundle(tmp_path)
    monkeypatch.chdir(root)

    assert (
        main(
            [
                "import-identifier-mapping",
                str(bundle),
                "--thread",
                "story_synthetic_001",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert output == "Identifier mapping imported: one immutable run and one sidecar.\n"
    assert "synthetic_one" not in output


def test_cli_reports_incomplete_rollback_truthfully(monkeypatch, capsys) -> None:
    def fail(*args, **kwargs):
        raise IdentifierMappingRollbackError("private sentinel")

    monkeypatch.setattr(cli_module, "import_identifier_mapping", fail)
    assert (
        main(
            [
                "import-identifier-mapping",
                "private-bundle.json",
                "--thread",
                "story_synthetic_001",
            ]
        )
        == 1
    )
    output = capsys.readouterr().out
    assert "rollback is incomplete" in output
    assert "private sentinel" not in output
    assert "no records were written" not in output


def test_fixture_method_has_a_tracked_method_file() -> None:
    bundle = load_identifier_mapping_bundle(FIXTURE)
    root = Path(__file__).resolve().parents[1]

    assert bundle.provenance is not None
    assert (root / "methods" / f"{METHOD_VERSION}.md").is_file()
