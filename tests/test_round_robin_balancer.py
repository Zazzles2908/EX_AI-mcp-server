from providers.balancer import RoundRobinBalancer


def test_round_robin_balancer_cycles():
    rr = RoundRobinBalancer(["e1", "e2", "e3"])
    seq = [rr.next() for _ in range(5)]
    assert seq == ["e1", "e2", "e3", "e1", "e2"]

