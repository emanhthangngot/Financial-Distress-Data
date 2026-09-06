"""Configuration contract for the dedicated Postgres -> Flink CDC path."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field


class CDCConfigError(ValueError):
    """Raised when CDC connector settings are unsafe or incomplete."""


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class CDCConfig:
    """Dedicated logical-replication source and Iceberg sink settings.

    ADR-013 (amended 2026-09-05): the CDC path is Debezium (a standalone Kafka Connect
    connector) -> Kafka -> Flink, not a Flink-embedded CDC connector reading Postgres
    directly. ``debezium_connector_config()`` is the connector registered with Kafka
    Connect; ``flink_kafka_source_properties()`` is what Flink actually consumes — a
    Kafka topic, never a direct Postgres connection.
    """

    host: str = "cdc-postgres"
    port: int = 5432
    database: str = "financial_distress_cdc"
    user: str = "cdc_reader"
    password: str | None = field(default=None, repr=False)
    slot_name: str = "financial_distress_cdc_slot"
    publication_name: str = "financial_distress_cdc_publication"
    table_include_list: tuple[str, ...] = ("public.financial_events",)
    iceberg_catalog_uri: str = "http://lakekeeper:8181/catalog"
    iceberg_namespace: str = "platform"
    iceberg_table: str = "cdc_bronze"
    server_id: int = 5401
    snapshot_mode: str = "initial"
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_prefix: str = "financial-distress-cdc"
    kafka_consumer_group: str = "flink-cdc-consumer"

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise CDCConfigError("host must not be empty")
        try:
            port = int(self.port)
        except (TypeError, ValueError) as exc:
            raise CDCConfigError("port must be an integer") from exc
        if not 1 <= port <= 65535:
            raise CDCConfigError("port must be between 1 and 65535")
        if self.server_id <= 0:
            raise CDCConfigError("server_id must be positive")
        for field_name in ("database", "user", "slot_name", "publication_name"):
            value = str(getattr(self, field_name))
            if not _IDENTIFIER.fullmatch(value):
                raise CDCConfigError(f"invalid {field_name}: {value!r}")
        if not self.table_include_list:
            raise CDCConfigError("table_include_list must contain at least one table")
        if any(not _IDENTIFIER.fullmatch(table) for table in self.table_include_list):
            raise CDCConfigError("table_include_list contains an invalid identifier")
        if self.snapshot_mode not in {"initial", "never", "parallel"}:
            raise CDCConfigError("snapshot_mode must be initial, parallel or never")
        if not self.iceberg_catalog_uri.startswith(("http://", "https://")):
            raise CDCConfigError("iceberg_catalog_uri must be an http(s) URL")
        if not self.iceberg_namespace or not self.iceberg_table:
            raise CDCConfigError("Iceberg namespace and table must not be empty")

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> CDCConfig:
        """Parse a mapping, accepting comma-separated table lists."""
        payload = dict(values)
        if "table_include_list" in payload and isinstance(payload["table_include_list"], str):
            payload["table_include_list"] = tuple(
                item.strip()
                for item in str(payload["table_include_list"]).split(",")
                if item.strip()
            )
        if "port" in payload:
            payload["port"] = int(payload["port"])
        if "server_id" in payload:
            payload["server_id"] = int(payload["server_id"])
        return cls(**payload)  # type: ignore[arg-type]

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> CDCConfig:
        env = os.environ if environ is None else environ
        return cls.from_mapping(
            {
                "host": env.get("CDC_POSTGRES_HOST", "cdc-postgres"),
                "port": env.get("CDC_POSTGRES_PORT", "5432"),
                "database": env.get("CDC_POSTGRES_DB", "financial_distress_cdc"),
                "user": env.get("CDC_POSTGRES_USER", "cdc_reader"),
                "password": env.get("CDC_POSTGRES_PASSWORD"),
                "slot_name": env.get("CDC_REPLICATION_SLOT", "financial_distress_cdc_slot"),
                "publication_name": env.get(
                    "CDC_PUBLICATION", "financial_distress_cdc_publication"
                ),
                "table_include_list": env.get("CDC_TABLE_INCLUDE_LIST", "public.financial_events"),
                "iceberg_catalog_uri": env.get(
                    "ICEBERG_CATALOG_URI", "http://lakekeeper:8181/catalog"
                ),
                "iceberg_namespace": env.get("CDC_ICEBERG_NAMESPACE", "platform"),
                "iceberg_table": env.get("CDC_ICEBERG_TABLE", "cdc_bronze"),
                "server_id": env.get("CDC_SERVER_ID", "5401"),
                "snapshot_mode": env.get("CDC_SNAPSHOT_MODE", "initial"),
                "kafka_bootstrap_servers": env.get("CDC_KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
                "kafka_topic_prefix": env.get("CDC_KAFKA_TOPIC_PREFIX", "financial-distress-cdc"),
                "kafka_consumer_group": env.get("CDC_KAFKA_CONSUMER_GROUP", "flink-cdc-consumer"),
            }
        )

    @property
    def iceberg_identifier(self) -> str:
        return f"{self.iceberg_namespace}.{self.iceberg_table}"

    def debezium_connector_config(self) -> dict[str, str]:
        """Kafka Connect registration payload for the standalone Debezium Postgres
        connector (ADR-013) — POSTed to Kafka Connect's ``/connectors`` endpoint. This
        connector, not Flink, is what reads Postgres's logical replication stream.
        """
        props = {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": self.host,
            "database.port": str(self.port),
            "database.user": self.user,
            "database.dbname": self.database,
            "slot.name": self.slot_name,
            "publication.name": self.publication_name,
            "table.include.list": ",".join(self.table_include_list),
            "snapshot.mode": self.snapshot_mode,
            "plugin.name": "pgoutput",
            "topic.prefix": self.kafka_topic_prefix,
        }
        if self.password is not None:
            props["database.password"] = self.password
        return props

    def flink_kafka_source_properties(self) -> dict[str, str]:
        """Flink Kafka table-source options — the only thing Flink actually connects to.

        Never a direct Postgres connection: Flink consumes the topic Debezium (not Flink)
        populates, decoupling Debezium's connector lifecycle from the Flink job's.
        """
        table_name = self.table_include_list[0].split(".")[-1]
        return {
            "connector": "kafka",
            "topic": f"{self.kafka_topic_prefix}.{self.database}.{table_name}",
            "properties.bootstrap.servers": self.kafka_bootstrap_servers,
            "properties.group.id": self.kafka_consumer_group,
            "format": "debezium-json",
            "scan.startup.mode": (
                "earliest-offset" if self.snapshot_mode != "never" else "latest-offset"
            ),
        }

    def sink_properties(self) -> dict[str, str]:
        """Return the Iceberg REST sink contract consumed by the Flink job."""
        return {
            "catalog-type": "rest",
            "uri": self.iceberg_catalog_uri,
            "catalog-name": "lakekeeper",
            "namespace": self.iceberg_namespace,
            "table": self.iceberg_table,
            "write.upsert.enabled": "true",
        }

    def validate_logical_replication(self, wal_level: str = "logical") -> None:
        """Fail fast when a source instance is not configured for Postgres CDC."""
        if wal_level.lower() != "logical":
            raise CDCConfigError("CDC Postgres requires wal_level=logical")


__all__ = ["CDCConfig", "CDCConfigError"]
