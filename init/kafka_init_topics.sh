#!/usr/bin/env bash
set -euo pipefail

BROKER="${BROKER:-kafka:9092}"
PARTITIONS="${PARTITIONS:-3}"
REPLICATION_FACTOR="${REPLICATION_FACTOR:-1}"

topics=(
  "financial.price_events"
  "financial.news_events"
  "financial.alert_events"
)

for topic in "${topics[@]}"; do
  until /opt/kafka/bin/kafka-topics.sh \
      --bootstrap-server "${BROKER}" \
      --create \
      --if-not-exists \
      --topic "${topic}" \
      --partitions "${PARTITIONS}" \
      --replication-factor "${REPLICATION_FACTOR}"; do
    sleep 2
  done
done
