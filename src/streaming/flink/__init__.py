"""Stage 1 Flink integration (opt-in).

Wires Apache Flink as a streaming option alongside the existing Kafka
MicroBatchConsumer path. Flink is OFF by default; toggle ENABLE_FLINK=1
to switch DAG 04 and friends to submit jobs to the local Flink cluster.
"""
