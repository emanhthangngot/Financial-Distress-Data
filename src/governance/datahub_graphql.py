"""Small GraphQL client for DataHub contract publication and verification."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DataHubGraphQLError(RuntimeError):
    """Raised when DataHub rejects or cannot serve a GraphQL operation."""


def execute_graphql(
    server: str,
    query: str,
    variables: dict[str, Any],
    *,
    token: str | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    """Execute one GraphQL request and reject HTTP and GraphQL errors."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"{server.rstrip('/')}/api/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise DataHubGraphQLError(f"DataHub GraphQL request failed: {exc}") from exc
    if payload.get("errors"):
        raise DataHubGraphQLError(f"DataHub GraphQL operation returned errors: {payload['errors']}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise DataHubGraphQLError("DataHub GraphQL response has no data object")
    return data


def upsert_data_contracts(
    server: str,
    contracts: dict[str, dict[str, str]],
    *,
    token: str | None = None,
) -> dict[str, str]:
    """Bundle each pipeline's schema and volume assertions into a contract."""
    mutation = """
    mutation UpsertCourseworkDataContract($input: UpsertDataContractInput!) {
      upsertDataContract(input: $input) { urn }
    }
    """
    contract_urns = {}
    for pipeline, contract in contracts.items():
        data = execute_graphql(
            server,
            mutation,
            {
                "input": {
                    "entityUrn": contract["dataset"],
                    "schema": [{"assertionUrn": contract["schema_assertion"]}],
                    "dataQuality": [{"assertionUrn": contract["volume_assertion"]}],
                }
            },
            token=token,
        )
        result = data.get("upsertDataContract")
        if not isinstance(result, dict) or not result.get("urn"):
            raise DataHubGraphQLError(f"DataHub did not return a contract URN for {pipeline}")
        contract_urns[pipeline] = result["urn"]
    return contract_urns


def verify_governance_entities(
    server: str,
    contracts: dict[str, dict[str, str]],
    *,
    token: str | None = None,
) -> dict[str, Any]:
    """Verify representative datasets and their contracts are queryable."""
    query = """
    query VerifyCourseworkDataset($urn: String!) {
      dataset(urn: $urn) {
        urn
        schemaMetadata { fields { fieldPath } }
        lineage(input: {direction: UPSTREAM, start: 0, count: 100}) { total }
        assertions(start: 0, count: 100) { total }
        contract { urn }
      }
    }
    """
    datasets = {}
    for pipeline, contract in contracts.items():
        data = execute_graphql(
            server,
            query,
            {"urn": contract["dataset"]},
            token=token,
        )
        dataset = data.get("dataset")
        if not isinstance(dataset, dict) or dataset.get("urn") != contract["dataset"]:
            raise DataHubGraphQLError(f"Representative dataset is not queryable for {pipeline}")
        if not dataset.get("schemaMetadata", {}).get("fields"):
            raise DataHubGraphQLError(f"Schema metadata is missing for {pipeline}")
        dataset_contract = dataset.get("contract") or {}
        if not dataset_contract.get("urn"):
            raise DataHubGraphQLError(f"Data contract is missing for {pipeline}")
        assertion_count = (dataset.get("assertions") or {}).get("total", 0)
        if assertion_count < 2:
            raise DataHubGraphQLError(f"Expected schema and volume assertions for {pipeline}")
        upstream_count = (dataset.get("lineage") or {}).get("total", 0)
        if upstream_count < 1:
            raise DataHubGraphQLError(f"Upstream lineage is missing for {pipeline}")
        datasets[pipeline] = {
            "urn": dataset["urn"],
            "contract_urn": dataset_contract["urn"],
            "field_count": len(dataset["schemaMetadata"]["fields"]),
            "assertion_count": assertion_count,
            "upstream_count": upstream_count,
        }
    return {"status": "pass", "datasets": datasets}
