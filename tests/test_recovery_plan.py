from dr.recovery_plan import RecoveryPlan


def test_recovery_plan_simulation():
    rp = RecoveryPlan(rto_minutes=30, rpo_minutes=5)
    ok, msg = rp.simulate_restore(backup_available=True, infra_ok=True)
    assert ok is True and "success" in msg.lower()
    ok2, _ = rp.simulate_restore(backup_available=False, infra_ok=True)
    assert ok2 is False

