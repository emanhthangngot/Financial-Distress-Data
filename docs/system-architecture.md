# System Architecture

The diagram uses only deployable runtime units as major nodes. Arrows are
numbered in execution order and name the payload crossing each boundary.

![Deployment architecture](../images/architecture/system_deployment_diagram.png)

## Runtime Boundaries

- Airflow owns orchestration, validation gates, retries, and publication order.
- Spark owns bounded Bronze-to-Silver/Gold and offline feature computation.
- Flink owns event-time streaming windows, late routing, and TTL deduplication.
- MinIO is the durable lakehouse boundary; PostgreSQL stores operational metadata.
- DataHub stores catalog, ownership, pipeline lineage, assertions, and contracts.
- DuckDB/DBeaver is a reviewer inspection surface, not a production service.

The executable behavior and evidence are detailed in the generator, Spark,
Flink, orchestration, governance, and schema documents linked from the README.
