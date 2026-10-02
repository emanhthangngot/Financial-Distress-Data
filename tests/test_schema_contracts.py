from src.metadata.schema_registry import InMemorySchemaRegistry


def test_financial_statement_contract_allows_statement_type():
    contract = InMemorySchemaRegistry().get_current("financial_statements")

    assert "statement_type" in contract.nullable


def test_financial_statement_contract_preserves_synthetic_provenance() -> None:
    contract = InMemorySchemaRegistry().get_current("financial_statements")

    row = contract.validate_row(
        {
            "ticker": "AAA",
            "report_period": "2025Q4",
            "fiscal_year": 2025,
            "fiscal_quarter": 4,
            "total_assets": 100,
            "total_liabilities": 50,
            "equity": 50,
            "created_ts": "2026-01-01T00:00:00+00:00",
            "source_system": "generator",
            "is_synthetic": True,
        }
    )

    assert row["source_system"] == "generator"
    assert row["is_synthetic"] is True
