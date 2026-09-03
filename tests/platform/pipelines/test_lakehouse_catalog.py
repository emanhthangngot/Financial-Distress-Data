from __future__ import annotations

from src.lakehouse.catalog import CatalogConfig, ConcurrentCommitError, load_catalog
from src.lakehouse.snapshots import diff_snapshots, read_as_of
from src.lakehouse.tables import register_phase2_tables


def test_platform_tables_register_and_time_travel() -> None:
    catalog = load_catalog(CatalogConfig(uri="http://localhost:8181/catalog"))
    tables = register_phase2_tables(catalog)
    table = tables["phase2.features"]
    first = table.append(
        [
            {
                "ticker": "AAA",
                "event_timestamp": "2026-01-01T00:00:00Z",
                "created_ts": "2026-01-01T00:00:01Z",
                "feature_value": 1.0,
            }
        ]
    )
    second = table.append(
        [
            {
                "ticker": "BBB",
                "event_timestamp": "2026-01-01T00:00:00Z",
                "created_ts": "2026-01-01T00:00:01Z",
                "feature_value": 2.0,
            }
        ],
        expected_snapshot_id=first.snapshot_id,
    )
    assert read_as_of(table, first.snapshot_id)[0]["ticker"] == "AAA"
    delta = diff_snapshots(table, first.snapshot_id, second.snapshot_id)
    assert delta.added_count == 1
    assert delta.removed_count == 0


def test_schema_evolution_is_additive_and_old_snapshot_remains_readable() -> None:
    catalog = load_catalog()
    table = register_phase2_tables(catalog)["phase2.labels"]
    snapshot = table.append(
        [
            {
                "ticker": "AAA",
                "event_timestamp": "2026-01-01T00:00:00Z",
                "created_ts": "2026-01-01T00:00:01Z",
                "distress_label": False,
            }
        ]
    )
    table.add_column("label_source", "string")
    current = table.append(
        [
            {
                "ticker": "AAA",
                "event_timestamp": "2026-01-02T00:00:00Z",
                "created_ts": "2026-01-02T00:00:01Z",
                "distress_label": True,
                "label_source": "cdc",
            }
        ]
    )
    # The old snapshot retains its original schema; a reader pinned to it does
    # not need to know about the newly added nullable column.
    assert "label_source" not in read_as_of(table, snapshot.snapshot_id)[0]
    assert read_as_of(table, current.snapshot_id)[-1]["label_source"] == "cdc"


def test_stale_expected_snapshot_is_rejected() -> None:
    table = load_catalog().create_table("phase2.t", {"id": "integer"})
    first = table.append([{"id": 1}])
    table.append([{"id": 2}], expected_snapshot_id=first.snapshot_id)
    try:
        table.append([{"id": 3}], expected_snapshot_id=first.snapshot_id)
    except ConcurrentCommitError:
        pass
    else:  # pragma: no cover - assertion style keeps exception type explicit
        raise AssertionError("stale commit should be rejected")
