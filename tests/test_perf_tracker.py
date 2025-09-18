from tools.unified.perf import PerfTracker
import time


def test_perf_tracker_records_entries():
    pt = PerfTracker()
    d = pt.timeit()
    time.sleep(0.01)
    dur = d(True, name="x")
    assert pt.records and pt.records[0]["name"] == "x" and dur > 0

