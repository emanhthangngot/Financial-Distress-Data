from src.metadata.schema_registry import InMemorySchemaRegistry


def test_financial_statement_contract_allows_statement_type():
    contract = InMemorySchemaRegistry().get_current("financial_statements")

    assert "statement_type" in contract.nullable
