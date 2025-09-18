from monitoring.worker_pool import WorkerPool


def test_worker_pool_decisions():
    wp = WorkerPool(min_workers=1, max_workers=3, current_workers=1)
    assert wp.decide([10], 2000) == "scale_up"
    assert wp.current_workers == 2
    assert wp.decide([0], 200) in ("hold", "scale_down")
    wp.current_workers = 3
    assert wp.decide([0], 200) in ("hold", "scale_down")

