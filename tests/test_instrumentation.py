from monitoring.file_sink import FileMetricsSink
from utils.instrumentation import instrument


def test_instrument_increments_and_times():
    sink = FileMetricsSink(path="logs/test_metrics_instrument.jsonl")
    with instrument(sink, op_name="op1", success_counter="op1.success"):
        pass
    sink.flush()
    assert sink.counters["op1.success"].value == 1
    assert sink.timers["latency.op1"].durations

