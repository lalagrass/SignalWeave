from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

import signalweave.agent_bundle as agent_bundle_module
from signalweave.agent_bundle import AgentBundleError, import_agent_bundle, load_agent_bundle
from signalweave.basket import load_basket
from signalweave.cli import main
from signalweave.export import export_baskets
from signalweave.runs import load_run
from signalweave.schema import load_candidate_event
from signalweave.threads import load_thread


FIXTURE = Path(__file__).parent / "fixtures" / "agent-bundle-v1.json"
SYNTHETIC_TRANSCRIPT = "Synthetic cited words. Additional synthetic context.\n\nUnused segment."


def _inputs(tmp_path: Path) -> tuple[Path, Path]:
    _initialize_repository(tmp_path)
    transcript = tmp_path / "private.md"
    transcript.write_text(SYNTHETIC_TRANSCRIPT, encoding="utf-8")
    bundle = tmp_path / "bundle.json"
    shutil.copyfile(FIXTURE, bundle)
    return transcript, bundle


def _initialize_repository(tmp_path: Path) -> None:
    if not (tmp_path / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("data/inbox/\ndata/private/\n", encoding="utf-8")


def _directories(tmp_path: Path) -> tuple[Path, Path, Path]:
    return (
        tmp_path / "data" / "inbox" / "events",
        tmp_path / "data" / "private" / "threads",
        tmp_path / "data" / "private" / "runs",
    )


def _import(tmp_path: Path):
    transcript, bundle = _inputs(tmp_path)
    return import_agent_bundle(
        transcript,
        bundle,
        source="source_synthetic",
        document_id="doc_synthetic_001",
        event_date="2026-09-13",
        workspace_root=tmp_path,
    )


def test_valid_agent_bundle_creates_one_run_events_story_and_basket(tmp_path: Path) -> None:
    result = _import(tmp_path)

    run = load_run(result.run_path)
    event = load_candidate_event(result.event_paths[0])
    thread = load_thread(result.thread_path.parent)
    basket = load_basket(result.thread_path.parent)

    assert len(result.event_paths) == 1
    assert run.provider == "openai"
    assert run.model_id == "gpt-synthetic-1"
    assert run.model_locality == "remote"
    assert run.method_version == "agent_bundle_v1"
    assert json.loads(run.output)["schema_version"] == 1
    assert {event.run_id, thread.run_id, basket.run_id} == {run.run_id}
    assert {event.review_status, thread.review_status, basket.review_status} == {"unreviewed"}
    assert {event.drafted_by, thread.drafted_by, basket.drafted_by} == {"agent_synthetic"}
    assert event.source == "source_synthetic"
    assert event.source_locator == "doc_synthetic_001#segment_1"


def test_span_mismatch_fails_before_creating_any_private_output(tmp_path: Path) -> None:
    transcript, bundle_path = _inputs(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["events"][0]["proposals"][0]["cited_span"] = "not present"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    inbox, threads, runs = _directories(tmp_path)

    with pytest.raises(AgentBundleError, match="cited span"):
        import_agent_bundle(
            transcript,
            bundle_path,
            source="source_synthetic",
            document_id="doc_synthetic_001",
            event_date="2026-09-13",
            workspace_root=tmp_path,
        )

    assert not inbox.exists()
    assert not threads.exists()
    assert not runs.exists()


def test_invalid_provenance_fails_before_creating_any_private_output(tmp_path: Path) -> None:
    transcript, bundle_path = _inputs(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    del bundle["provenance"]["model_id"]
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    inbox, threads, runs = _directories(tmp_path)

    with pytest.raises(AgentBundleError, match="invalid fields"):
        import_agent_bundle(
            transcript,
            bundle_path,
            source="source_synthetic",
            document_id="doc_synthetic_001",
            event_date="2026-09-13",
            workspace_root=tmp_path,
        )

    assert not inbox.exists()
    assert not threads.exists()
    assert not runs.exists()


def test_collision_is_detected_before_any_new_output_is_written(tmp_path: Path) -> None:
    transcript, bundle = _inputs(tmp_path)
    inbox, threads, runs = _directories(tmp_path)
    inbox.mkdir(parents=True)
    existing = inbox / "evt_synthetic_001.yaml"
    existing.write_text("pre-existing private record", encoding="utf-8")

    with pytest.raises(AgentBundleError, match="collides"):
        import_agent_bundle(
            transcript,
            bundle,
            source="source_synthetic",
            document_id="doc_synthetic_001",
            event_date="2026-09-13",
            workspace_root=tmp_path,
        )

    assert existing.read_text(encoding="utf-8") == "pre-existing private record"
    assert not threads.exists()
    assert not list(runs.glob("*.yaml"))


def test_failed_write_rolls_back_a_destination_created_before_the_error(
    tmp_path: Path, monkeypatch
) -> None:
    transcript, bundle = _inputs(tmp_path)
    inbox, threads, runs = _directories(tmp_path)
    original_write = agent_bundle_module.write_candidate_draft

    def write_then_fail(record, directory):
        original_write(record, directory)
        raise OSError("synthetic write failure")

    monkeypatch.setattr(agent_bundle_module, "write_candidate_draft", write_then_fail)

    with pytest.raises(AgentBundleError, match="could not complete"):
        import_agent_bundle(
            transcript,
            bundle,
            source="source_synthetic",
            document_id="doc_synthetic_001",
            event_date="2026-09-13",
            workspace_root=tmp_path,
        )

    assert not inbox.exists()
    assert not threads.exists()
    assert not list(runs.glob("*.yaml"))


def test_importer_rejects_a_private_root_that_resolves_outside_its_workspace(tmp_path: Path) -> None:
    transcript, bundle = _inputs(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}_public_output"
    outside.mkdir()
    try:
        (tmp_path / "data").symlink_to(outside, target_is_directory=True)
        with pytest.raises(AgentBundleError, match="exact private workspace roots"):
            import_agent_bundle(
                transcript,
                bundle,
                source="source_synthetic",
                document_id="doc_synthetic_001",
                event_date="2026-09-13",
                workspace_root=tmp_path,
            )
        assert not any(outside.iterdir())
    finally:
        shutil.rmtree(outside)


def test_importer_rejects_an_internal_symlink_to_an_unignored_path(tmp_path: Path) -> None:
    transcript, bundle = _inputs(tmp_path)
    internal_public = tmp_path / "docs" / "data"
    internal_public.mkdir(parents=True)
    (tmp_path / "data").symlink_to(internal_public, target_is_directory=True)

    with pytest.raises(AgentBundleError, match="exact private workspace roots"):
        import_agent_bundle(
            transcript,
            bundle,
            source="source_synthetic",
            document_id="doc_synthetic_001",
            event_date="2026-09-13",
            workspace_root=tmp_path,
        )

    assert not any(internal_public.iterdir())


def test_importer_rejects_a_nested_non_root_workspace_before_any_write(tmp_path: Path) -> None:
    transcript, bundle = _inputs(tmp_path)
    nested = tmp_path / "docs"
    nested.mkdir()

    with pytest.raises(AgentBundleError, match="Git workspace top-level"):
        import_agent_bundle(
            transcript,
            bundle,
            source="source_synthetic",
            document_id="doc_synthetic_001",
            event_date="2026-09-13",
            workspace_root=nested,
        )

    assert not (nested / "data").exists()


def test_concurrent_import_lock_refuses_without_removing_existing_records(tmp_path: Path) -> None:
    transcript, bundle = _inputs(tmp_path)
    inbox, threads, runs = _directories(tmp_path)

    with agent_bundle_module._workspace_import_lock(runs):
        with pytest.raises(AgentBundleError, match="already in progress"):
            import_agent_bundle(
                transcript,
                bundle,
                source="source_synthetic",
                document_id="doc_synthetic_001",
                event_date="2026-09-13",
                workspace_root=tmp_path,
            )

    assert not list(inbox.glob("*.yaml"))
    assert not threads.exists()
    assert not list(runs.glob("*.yaml"))


def test_cli_import_uses_no_direct_api_path(tmp_path: Path, monkeypatch, capsys) -> None:
    transcript, bundle = _inputs(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "import-agent-bundle",
                str(transcript),
                str(bundle),
                "--source",
                "source_synthetic",
                "--document-id",
                "doc_synthetic_001",
                "--date",
                "2026-09-13",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "Agent bundle imported: 1 event(s), one story, and one basket." in output
    assert "Synthetic cited words" not in output


def test_agent_bundle_export_requires_a_separate_identity_mapping(tmp_path: Path) -> None:
    _import(tmp_path)
    _, threads, runs = _directories(tmp_path)
    with pytest.raises(ValueError, match="no active identifier mapping"):
        export_baskets(
            threads,
            runs,
            tmp_path / "data" / "private" / "identifier-mappings",
            as_of=__import__("datetime").date(2026, 9, 13),
        )


def test_agent_bundle_method_version_has_a_tracked_method_file() -> None:
    root = Path(__file__).resolve().parents[1]
    method = root / "methods" / f"{agent_bundle_module.METHOD_VERSION}.md"

    assert method.is_file()


def test_bundle_rejects_unknown_or_incomplete_shapes(tmp_path: Path) -> None:
    _, bundle_path = _inputs(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["unexpected"] = "private-looking value"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    with pytest.raises(AgentBundleError, match="invalid fields"):
        load_agent_bundle(bundle_path)
