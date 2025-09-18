import json
from pathlib import Path
from monitoring.file_sink import FileMetricsSink


def test_file_metrics_sink_flush():
    path = Path("logs/test_metrics.jsonl")
    if path.exists():
        path.unlink()
    m = FileMetricsSink(path=str(path), max_bytes=10_000)
    m.counter("requests").inc(2)
    m.timer("latency").durations.extend([0.1, 0.2])
    m.flush()
    assert path.exists()
    data = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert data and data[-1]["counters"]["requests"] == 2

