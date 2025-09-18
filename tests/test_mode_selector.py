from tools.reasoning.mode_selector import select_mode


def test_mode_selector():
    assert select_mode({"has_images": True}) == "balanced"
    assert select_mode({"long_context": True}) == "deep"
    assert select_mode({}) == "fast"

