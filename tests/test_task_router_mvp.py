from routing.task_router import IntelligentTaskRouter


def test_router_multimodal_routes_to_zai():
    r = IntelligentTaskRouter()
    assert r.select_platform({"has_images": True}) == "zai"


def test_router_long_context_routes_to_moonshot():
    r = IntelligentTaskRouter()
    req = {"messages": ["x" * (128_001 * 4)]}
    assert r.select_platform(req) == "moonshot"


def test_router_task_type_default():
    r = IntelligentTaskRouter()
    assert r.select_platform({"task_type": "code_generation"}) == "moonshot"

