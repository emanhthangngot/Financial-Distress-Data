from src.streaming.events import StreamEvent
from src.streaming.kafka_to_bronze_consumer import MicroBatchConsumer


def test_microbatch_flushes_by_record_count():
    consumer = MicroBatchConsumer(flush_record_count=2)
    first = StreamEvent.price_update(
        "AAA", "2026-01-01T09:00:00+00:00", "2026-01-01T09:00:01+00:00", 10.0, 100
    )
    second = StreamEvent.price_update(
        "AAA", "2026-01-01T09:00:02+00:00", "2026-01-01T09:00:03+00:00", 10.1, 120
    )
    assert consumer.add_event(first.as_record()) == []
    batches = consumer.add_event(second.as_record())
    assert len(batches) == 1
    assert batches[0]["record_count"] == 2
    assert "event_date=2026-01-01" in batches[0]["bronze_path"]
