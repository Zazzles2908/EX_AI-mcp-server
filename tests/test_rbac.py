from security.rbac import RBAC


def test_rbac_policies():
    r = RBAC()
    assert r.can_execute("analyze", "developer") is True
    assert r.can_execute("consensus", "viewer") is False
    assert r.can_execute("anything", "admin") is True

