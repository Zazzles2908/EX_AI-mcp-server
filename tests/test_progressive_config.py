from ui.progressive_config import DisclosureConfig


def test_progressive_config_levels():
    minimal = DisclosureConfig(level="minimal")
    normal = DisclosureConfig(level="normal")
    verbose = DisclosureConfig(level="verbose")

    assert minimal.should_show("minimal", 0) is True
    assert minimal.should_show("normal", 0) is False
    assert normal.should_show("normal", 1) is True
    assert verbose.should_show("verbose", 2) is True

