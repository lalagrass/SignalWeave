from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from signalweave.basket import (
    Basket,
    BasketValidationError,
    create_basket,
    load_basket,
    write_basket,
)
from signalweave.threads import create_thread, write_thread


def make_thread(threads_directory: Path, thread_id: str = "story_doc_2026_001") -> None:
    thread = create_thread(
        thread_id=thread_id,
        mechanism="A synthetic mechanism.",
        open_question="A synthetic question?",
        invalidation_conditions=["A synthetic invalidation condition."],
        groups=["synthetic upstream suppliers"],
        market_sentiment="Synthetic sentiment.",
        review_date="2026-12-15",
        created_by="model_synthetic",
        drafted_by="model_synthetic",
        run_id="run_synthetic001",
        created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    write_thread(thread, threads_directory)


def basket(thread_id: str = "story_doc_2026_001", instruments: list[str] | None = None) -> Basket:
    return create_basket(
        thread_id=thread_id,
        instruments=instruments if instruments is not None else ["tsmc", "asml"],
        drafted_by="model_synthetic",
        run_id="run_synthetic002",
        created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )


def test_basket_review_status_is_always_unreviewed() -> None:
    record = basket()

    assert record.review_status == "unreviewed"


def test_basket_may_be_empty() -> None:
    record = basket(instruments=[])

    assert record.instruments == ()


def test_basket_rejects_a_review_status_other_than_unreviewed() -> None:
    with pytest.raises(BasketValidationError, match="unreviewed"):
        Basket.from_mapping(
            {
                "thread_id": "story_doc_2026_001",
                "instruments": ["tsmc"],
                "review_status": "accepted",
                "drafted_by": "model_synthetic",
                "run_id": "run_synthetic002",
                "created_at": "2026-09-11T00:00:00+00:00",
            }
        )


def test_write_basket_requires_an_existing_thread(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        write_basket(basket(), threads_directory)


def test_write_basket_never_overwrites(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    make_thread(threads_directory)
    record = basket()

    path = write_basket(record, threads_directory)

    assert path == threads_directory / "story_doc_2026_001" / "basket.yaml"
    with pytest.raises(FileExistsError, match="already exists"):
        write_basket(record, threads_directory)


def test_basket_round_trips_and_has_no_weights_or_ordering_fields(tmp_path: Path) -> None:
    threads_directory = tmp_path / "data" / "private" / "threads"
    make_thread(threads_directory)
    path = write_basket(basket(), threads_directory)

    loaded = load_basket(threads_directory / "story_doc_2026_001")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert loaded.instruments == ("tsmc", "asml")
    assert set(raw.keys()) == {
        "thread_id",
        "instruments",
        "review_status",
        "drafted_by",
        "run_id",
        "created_at",
    }


def test_basket_accepts_exchange_codes_alongside_plain_names() -> None:
    instruments = ["2330", "AAPL", "BRK.B", "tsmc", "hon_hai", "00631L"]

    record = basket(instruments=instruments)

    assert record.instruments == tuple(instruments)


@pytest.mark.parametrize("instrument", [".2330", "2330.", "2330__L", ""])
def test_basket_rejects_a_malformed_instrument(instrument: str) -> None:
    with pytest.raises(BasketValidationError, match="alphanumeric"):
        basket(instruments=[instrument])


@pytest.mark.parametrize("field", ["thread_id", "drafted_by", "run_id"])
@pytest.mark.parametrize("value", ["2330", "AAPL"])
def test_baskets_own_identifiers_stay_lowercase(field: str, value: str) -> None:
    record = {
        "thread_id": "story_doc_2026_001",
        "instruments": ["2330"],
        "review_status": "unreviewed",
        "drafted_by": "model_synthetic",
        "run_id": "run_synthetic002",
        "created_at": "2026-09-11T00:00:00+00:00",
    }
    record[field] = value

    with pytest.raises(BasketValidationError, match="lowercase"):
        Basket.from_mapping(record)
