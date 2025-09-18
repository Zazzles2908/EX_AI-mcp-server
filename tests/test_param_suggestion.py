from tools.unified.param_suggestion import suggest_params


def test_param_suggestion_multimodal():
    p = suggest_params("Analyze this image: cat.png")
    assert p["has_images"] is True and p["task_type"] == "multimodal_reasoning"


def test_param_suggestion_long_context():
    prompt = "x" * (128_100 // 4)
    p = suggest_params(prompt)
    assert p["long_context"] is True and p["task_type"] == "long_context_analysis"

