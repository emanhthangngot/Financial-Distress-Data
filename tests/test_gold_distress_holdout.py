"""gold.distress_holdout freeze contract (phase-04-data-plane.md, AC:
"holdout-v1 resolves to byte-identical time-travel reads and is pinned to a
knowledge-time cutoff")."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.lakehouse.catalog import CatalogError, LocalIcebergCatalog
from src.lakehouse.holdout import (
    HOLDOUT_TAG,
    HoldoutFreezeError,
    filter_to_knowledge_cutoff,
    freeze_distress_holdout,
    read_distress_holdout,
)


def _row(ticker: str, period: str, known_from: str, label: int) -> dict:
    return {
        "ticker": ticker,
        "report_period": period,
        "known_from_ts": known_from,
        "distress_label": label,
    }


def test_filter_to_knowledge_cutoff_excludes_rows_known_after_cutoff() -> None:
    rows = [
        _row("AAA", "2023Q2", "2023-08-01T00:00:00+00:00", 0),
        _row("AAA", "2023Q2", "2024-03-01T00:00:00+00:00", 1),  # restated, known later
    ]
    cutoff = datetime(2023, 12, 1, tzinfo=UTC)

    kept = filter_to_knowledge_cutoff(rows, cutoff)

    assert len(kept) == 1
    assert kept[0]["known_from_ts"] == "2023-08-01T00:00:00+00:00"


def test_filter_raises_on_missing_known_from_ts() -> None:
    rows = [{"ticker": "AAA", "report_period": "2023Q2", "known_from_ts": None}]
    with pytest.raises(HoldoutFreezeError, match="known_from_ts"):
        filter_to_knowledge_cutoff(rows, datetime(2024, 1, 1, tzinfo=UTC))


def test_freeze_raises_when_nothing_survives_cutoff() -> None:
    rows = [_row("AAA", "2023Q2", "2025-01-01T00:00:00+00:00", 1)]
    catalog = LocalIcebergCatalog()
    with pytest.raises(HoldoutFreezeError, match="refusing to freeze"):
        freeze_distress_holdout(catalog, rows, knowledge_cutoff=datetime(2024, 1, 1, tzinfo=UTC))


def test_freeze_and_read_round_trips_the_filtered_rows() -> None:
    rows = [
        _row("AAA", "2023Q2", "2023-08-01T00:00:00+00:00", 0),
        _row("BBB", "2023Q2", "2023-09-01T00:00:00+00:00", 1),
        _row("CCC", "2023Q2", "2024-06-01T00:00:00+00:00", 1),  # excluded, known too late
    ]
    catalog = LocalIcebergCatalog()

    result = freeze_distress_holdout(
        catalog, rows, knowledge_cutoff=datetime(2023, 12, 1, tzinfo=UTC)
    )

    assert result.tag == HOLDOUT_TAG
    assert result.row_count == 2
    read_back = read_distress_holdout(catalog)
    assert {r["ticker"] for r in read_back} == {"AAA", "BBB"}


def test_re_freezing_identical_input_yields_the_same_snapshot_id() -> None:
    rows = [_row("AAA", "2023Q2", "2023-08-01T00:00:00+00:00", 0)]
    cutoff = datetime(2023, 12, 1, tzinfo=UTC)

    catalog_a = LocalIcebergCatalog()
    result_a = freeze_distress_holdout(catalog_a, rows, knowledge_cutoff=cutoff)

    catalog_b = LocalIcebergCatalog()
    result_b = freeze_distress_holdout(catalog_b, rows, knowledge_cutoff=cutoff)

    assert result_a.snapshot_id == result_b.snapshot_id


def test_tag_read_is_byte_identical_across_repeated_reads() -> None:
    rows = [_row("AAA", "2023Q2", "2023-08-01T00:00:00+00:00", 0)]
    catalog = LocalIcebergCatalog()
    freeze_distress_holdout(catalog, rows, knowledge_cutoff=datetime(2023, 12, 1, tzinfo=UTC))

    first_read = read_distress_holdout(catalog)
    second_read = read_distress_holdout(catalog)
    assert first_read == second_read
    assert first_read is not second_read  # each read returns an independent copy


def test_holdout_tag_is_pinned_even_after_later_unrelated_commits() -> None:
    """The tag must keep resolving to the frozen snapshot even if the table
    is later replaced again — proving holdout-v1 is a real pin, not just
    'whatever the table currently holds'."""
    rows = [_row("AAA", "2023Q2", "2023-08-01T00:00:00+00:00", 0)]
    catalog = LocalIcebergCatalog()
    freeze_distress_holdout(catalog, rows, knowledge_cutoff=datetime(2023, 12, 1, tzinfo=UTC))

    table = catalog.load_table("gold.distress_holdout")
    table.replace([_row("ZZZ", "2099Q1", "2099-01-01T00:00:00+00:00", 0)])

    pinned_read = read_distress_holdout(catalog)
    assert {r["ticker"] for r in pinned_read} == {"AAA"}
    assert table.read()[0]["ticker"] == "ZZZ"  # main history moved on; the tag did not


def test_resolve_tag_raises_for_unknown_tag() -> None:
    catalog = LocalIcebergCatalog()
    table = catalog.create_table("gold.other", {"ticker": "string"})
    table.replace([{"ticker": "AAA"}])
    with pytest.raises(CatalogError, match="unknown tag"):
        table.resolve_tag("not-a-real-tag")
