#!/usr/bin/env python3
"""Bounded Kafka replay job proving the Stage 5 PyFlink streaming contracts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyflink.common import Duration, Encoder, Types, WatermarkStrategy  # noqa: E402
from pyflink.common.serialization import SimpleStringSchema  # noqa: E402
from pyflink.datastream import OutputTag, StreamExecutionEnvironment  # noqa: E402
from pyflink.datastream.connectors.file_system import FileSink  # noqa: E402
from pyflink.datastream.connectors.kafka import (  # noqa: E402
    KafkaOffsetsInitializer,
    KafkaSource,
)
from pyflink.datastream.functions import (  # noqa: E402
    AggregateFunction,
    KeyedProcessFunction,
    ProcessFunction,
    ProcessWindowFunction,
    RuntimeContext,
)
from pyflink.datastream.state import StateTtlConfig, ValueStateDescriptor  # noqa: E402
from pyflink.datastream.window import Time, TumblingEventTimeWindows  # noqa: E402

from src.streaming.flink_contract import (  # noqa: E402
    load_flink_streaming_config,
    price_event_error,
)

INVALID = OutputTag("invalid-records", Types.STRING())
DUPLICATE = OutputTag("duplicate-events", Types.STRING())
TOO_LATE = OutputTag("too-late-events", Types.PICKLED_BYTE_ARRAY())


class ParsePriceEvent(ProcessFunction):
    def process_element(self, value: str, ctx: ProcessFunction.Context):
        try:
            event = json.loads(value)
            error = price_event_error(event)
            if error:
                raise ValueError(error)
            yield event
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            yield INVALID, json.dumps({"raw": value, "error": str(exc)}, sort_keys=True)


class EventTimestampAssigner:
    def extract_timestamp(self, value: dict[str, Any], record_timestamp: int) -> int:
        from datetime import datetime

        return int(datetime.fromisoformat(value["event_timestamp"]).timestamp() * 1000)


class DeduplicateEvents(KeyedProcessFunction):
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self.seen = None

    def open(self, runtime_context: RuntimeContext):
        ttl = (
            StateTtlConfig.new_builder(Time.seconds(self.ttl_seconds))
            .set_update_type(StateTtlConfig.UpdateType.OnCreateAndWrite)
            .build()
        )
        descriptor = ValueStateDescriptor("seen-event", Types.BOOLEAN())
        descriptor.enable_time_to_live(ttl)
        self.seen = runtime_context.get_state(descriptor)

    def process_element(self, value: dict[str, Any], ctx: KeyedProcessFunction.Context):
        if self.seen.value():
            yield DUPLICATE, json.dumps(value, sort_keys=True)
            return
        self.seen.update(True)
        yield value


class PriceAggregate(AggregateFunction):
    def create_accumulator(self):
        return 0, 0.0, 0

    def add(self, value: dict[str, Any], accumulator):
        count, price_sum, volume_sum = accumulator
        return count + 1, price_sum + float(value["price"]), volume_sum + int(value["volume"])

    def get_result(self, accumulator):
        return accumulator

    def merge(self, first, second):
        return tuple(left + right for left, right in zip(first, second, strict=True))


class RenderWindow(ProcessWindowFunction):
    def process(
        self,
        key: str,
        context: ProcessWindowFunction.Context,
        aggregates,
    ) -> Iterable[str]:
        count, price_sum, volume_sum = next(iter(aggregates))
        yield json.dumps(
            {
                "ticker": key,
                "window_start_epoch_ms": context.window().start,
                "window_end_epoch_ms": context.window().end,
                "event_count": count,
                "average_price": round(price_sum / count, 6),
                "total_volume": volume_sum,
            },
            sort_keys=True,
        )


def _sink(path: str) -> FileSink:
    return FileSink.for_row_format(path, Encoder.simple_string_encoder("UTF-8")).build()


def build_pipeline(
    env: StreamExecutionEnvironment,
    config_path: str,
    variant: str,
    *,
    continuous: bool = False,
):
    config = load_flink_streaming_config(config_path)
    settings = getattr(config, variant)
    env.set_parallelism(settings.parallelism)
    if settings.checkpointing:
        env.enable_checkpointing(config.checkpoint_interval_ms)

    source_builder = (
        KafkaSource.builder()
        .set_bootstrap_servers(config.kafka_bootstrap_servers)
        .set_topics(config.source_topic)
        .set_group_id(f"{config.consumer_group}-{variant}")
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
    )
    if not continuous:
        source_builder.set_bounded(KafkaOffsetsInitializer.latest())
    source = source_builder.build()
    raw = env.from_source(source, WatermarkStrategy.no_watermarks(), "kafka-price-events")
    parsed = raw.process(ParsePriceEvent(), output_type=Types.PICKLED_BYTE_ARRAY())
    parsed.get_side_output(INVALID).sink_to(_sink(f"{config.output_root}/{variant}/invalid"))
    watermarks = WatermarkStrategy.for_bounded_out_of_orderness(
        Duration.of_seconds(config.max_out_of_orderness_seconds)
    ).with_timestamp_assigner(EventTimestampAssigner())
    timed = parsed.assign_timestamps_and_watermarks(watermarks)

    if settings.deduplicate:
        clean = timed.key_by(lambda event: event["event_id"]).process(
            DeduplicateEvents(config.dedup_ttl_seconds),
            output_type=Types.PICKLED_BYTE_ARRAY(),
        )
        clean.get_side_output(DUPLICATE).sink_to(
            _sink(f"{config.output_root}/{variant}/duplicates")
        )
    else:
        clean = timed

    windows = (
        clean.key_by(lambda event: event["ticker"])
        .window(TumblingEventTimeWindows.of(Time.seconds(config.window_seconds)))
        .allowed_lateness(config.allowed_lateness_seconds * 1000)
        .side_output_late_data(TOO_LATE)
        .aggregate(PriceAggregate(), RenderWindow(), output_type=Types.STRING())
    )
    windows.sink_to(_sink(f"{config.output_root}/{variant}/windows"))
    windows.get_side_output(TOO_LATE).map(
        lambda event: json.dumps(event, sort_keys=True), output_type=Types.STRING()
    ).sink_to(_sink(f"{config.output_root}/{variant}/too-late"))
    return windows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/opt/flink/project/configs/flink-streaming.yaml")
    parser.add_argument("--variant", choices=("baseline", "optimized"), required=True)
    parser.add_argument("--continuous", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env = StreamExecutionEnvironment.get_execution_environment()
    build_pipeline(env, args.config, args.variant, continuous=args.continuous)
    env.execute(f"financial-distress-flink-{args.variant}")


if __name__ == "__main__":
    main()
