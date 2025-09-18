from audit.audit_logger import AuditLogger


def test_audit_logger_records():
    a = AuditLogger()
    a.log(user="u1", tool="analyze", params={"x": 1}, success=True)
    assert a.records and a.records[0]["user"] == "u1" and a.records[0]["success"] is True

