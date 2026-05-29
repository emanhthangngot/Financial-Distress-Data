from src.metadata.schema_registry import InMemorySchemaRegistry
from src.transforms.bronze_to_silver import bronze_to_silver


def test_schema_evolution_missing_nullable_field_is_allowed():
    contract = InMemorySchemaRegistry().get_current("financial_statements")
    silver, failed = bronze_to_silver(
        [
            {
                "ticker": "AAA",
                "report_period": "2025Q4",
                "fiscal_year": 2025,
                "fiscal_quarter": 4,
                "total_assets": 1000,
                "total_liabilities": 500,
                "equity": 500,
                "created_ts": "2026-01-01T00:00:00+00:00",
            }
        ],
        contract.required,
        contract.nullable,
        ["ticker", "report_period"],
    )
    assert failed == []
    assert silver[0]["retained_earnings"] is None


def test_deduplicate_keeps_latest_created_ts():
    contract = InMemorySchemaRegistry().get_current("companies")
    silver, failed = bronze_to_silver(
        [
            {
                "ticker": "AAA",
                "company_name": "Old",
                "exchange": "HOSE",
                "created_ts": "2026-01-01T00:00:00+00:00",
            },
            {
                "ticker": "AAA",
                "company_name": "New",
                "exchange": "HOSE",
                "created_ts": "2026-01-02T00:00:00+00:00",
            },
        ],
        contract.required,
        contract.nullable,
        ["ticker"],
    )
    assert failed == []
    assert len(silver) == 1
    assert silver[0]["company_name"] == "New"
