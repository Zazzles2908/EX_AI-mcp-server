from nl.command_processor import parse_command


def test_parse_command_basic():
    d = parse_command("run tool=consensus steps=2 expert=true")
    assert d["action"] == "run"
    assert d["tool"] == "consensus"
    assert d["steps"] == 2
    assert d["expert"] is True

