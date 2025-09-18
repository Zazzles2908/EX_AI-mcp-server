from tools.cost.cost_optimizer import choose_model


def test_cost_optimizer_rules():
    assert choose_model({"has_images": True}).startswith("zai:")
    assert choose_model({"long_context": True}).startswith("moonshot:")
    assert choose_model({}).startswith("zai:")

