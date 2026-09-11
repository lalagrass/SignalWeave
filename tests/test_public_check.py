from pathlib import Path

from signalweave.public_check import violations


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
