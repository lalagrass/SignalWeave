from pathlib import Path

import pytest

from signalweave.public_check import (
    PublicCheckConfigurationError,
    is_configured,
    require_configuration,
    violations,
)


def test_flags_configured_private_terms_and_raw_sources(tmp_path: Path) -> None:
    (tmp_path / ".signalweave").mkdir()
    (tmp_path / ".signalweave" / "private_terms.txt").write_text("Secret Source\n")
    (tmp_path / "notes.md").write_text("Mention: secret source")
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "episode.srt").write_text("raw content")

    result = violations(tmp_path, paths=list(tmp_path.rglob("*")))

    assert "private term 'Secret Source' in notes.md" in result
    assert "blocked private path: data/raw/episode.srt" in result


def test_ignores_example_terms_and_accepts_synthetic_record(tmp_path: Path) -> None:
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "event.yaml").write_text("source: source_a\n")

    assert violations(tmp_path, paths=list(tmp_path.rglob("*"))) == []


def test_is_configured_reflects_the_private_terms_file(tmp_path: Path) -> None:
    assert is_configured(tmp_path) is False

    (tmp_path / ".signalweave").mkdir()
    (tmp_path / ".signalweave" / "private_terms.txt").write_text("term\n")

    assert is_configured(tmp_path) is True


def test_require_configuration_fails_loudly_when_unconfigured(tmp_path: Path) -> None:
    with pytest.raises(PublicCheckConfigurationError, match="private_terms.txt"):
        require_configuration(tmp_path, allow_unconfigured=False)


def test_require_configuration_allows_explicit_override(tmp_path: Path) -> None:
    require_configuration(tmp_path, allow_unconfigured=True)


def test_require_configuration_passes_when_configured(tmp_path: Path) -> None:
    (tmp_path / ".signalweave").mkdir()
    (tmp_path / ".signalweave" / "private_terms.txt").write_text("term\n")

    require_configuration(tmp_path, allow_unconfigured=False)


def test_violations_flags_a_concrete_private_zone_locator(tmp_path: Path) -> None:
    doc = tmp_path / "notes.md"
    doc.write_text("Walked through data/raw/real_source/2026-01-02.md today.")

    result = violations(tmp_path, paths=[doc])

    assert any("private-zone locator" in item and "real_source" in item for item in result)


def test_violations_allows_bare_zone_and_known_subfolder_references(tmp_path: Path) -> None:
    doc = tmp_path / "notes.md"
    doc.write_text(
        "Raw sources live under data/raw/. Candidate cards go to "
        "data/inbox/events/, reviews to data/inbox/reviews/, threads to "
        "data/private/threads/, worklogs to data/private/worklog/, and run "
        "records to data/private/runs/."
    )

    assert violations(tmp_path, paths=[doc]) == []


def test_violations_allows_the_bare_runs_zone_reference(tmp_path: Path) -> None:
    doc = tmp_path / "architecture.md"
    doc.write_text("Run records live in data/private/runs/, one file per run.")

    assert violations(tmp_path, paths=[doc]) == []


def test_violations_exempts_tests_and_examples_from_the_locator_check(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    fixture = tmp_path / "tests" / "test_something.py"
    fixture.write_text('assert path == "data/raw/episode.srt"\n')

    assert violations(tmp_path, paths=[fixture]) == []
