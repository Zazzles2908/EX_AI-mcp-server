from ui.suggestions import SuggestionEngine


def test_suggestions_engine_outputs_list():
    eng = SuggestionEngine()
    s1 = eng.generate({})
    s2 = eng.generate({"has_images": True})
    assert isinstance(s1, list) and s1
    assert any("multimodal" in x.lower() for x in eng.generate({"has_images": True}))

