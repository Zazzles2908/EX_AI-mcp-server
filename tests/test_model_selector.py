from tools.cost.model_selector import choose_model_data_driven


def test_choose_model_data_driven():
    sel = choose_model_data_driven({
        "zai:glm-4.5-flash": {"success_rate": 0.995, "p95_ms": 800},
        "moonshot:kimi-k2-0711-preview": {"success_rate": 0.990, "p95_ms": 600},
    })
    assert sel == "zai:glm-4.5-flash"

