import json

from app.engine.reasoner import ExpertSystem
from app.llm.fallback_parser import detect_lang, parse_keywords
from app.llm.narrator import narrate, verify
from app.llm.parser import ground, parse_with_llm
from app.schemas import UserRequest
from tests.conftest import FakeLLM


def test_matcher_handles_three_languages_and_quantities(matcher):
    assert dict(matcher.find_all("I have 3 eggs, 250g butter and 1 kg of flour")) == {"eggs": 3, "butter": 250, "all_purpose_flour": 1000}
    assert dict(matcher.find_all("J'ai des oeufs, du beurre et de la farine")).keys() == {"eggs", "butter", "all_purpose_flour"}
    found = dict(matcher.find_all("عندي سميد وماء الزهر و3 بيضات بالزبدة"))
    assert found.keys() == {"semolina", "orange_blossom_water", "eggs", "butter"}
    assert found["eggs"] == 3


def test_matcher_prefers_longest_match(matcher):
    assert [i for i, _ in matcher.find_all("coconut oil and coconut")] == ["coconut_oil", "desiccated_coconut"]
    assert matcher.resolve("Farine de ble") == "all_purpose_flour"
    assert matcher.resolve("buttr") == "butter"
    assert matcher.resolve("unicorn dust") is None


def test_keyword_parser_constraints_negation_and_time(matcher):
    req = parse_keywords("I have flour, sugar and butter but no eggs. My son is allergic to peanuts. Gluten-free please, under 45 minutes, for 8 people.", matcher)
    assert req.pantry_ids() == {"all_purpose_flour", "sugar", "butter"}
    assert req.avoid == ["peanuts"] and req.diets == ["gluten_free"]
    assert req.max_time == 45 and req.servings == 8


def test_keyword_parser_occasion_and_language(matcher):
    assert parse_keywords("عندي سميد وتمر، حاب حلويات للعيد", matcher).occasion == "eid"
    assert parse_keywords("gâteau pour l'anniversaire des enfants", matcher).occasion == "birthday"
    assert detect_lang("j'ai de la farine et des oeufs") == "fr"
    assert detect_lang("عندي دقيق") == "ar"


def test_ground_rejects_invalid_values_and_allergens(matcher):
    raw = {
        "lang": "fr",
        "pantry": [{"name": "oeufs", "qty": 2}, {"name": "cacahuètes"}, {"name": "dragon fruit"}],
        "diets": ["vegan", "keto"],
        "avoid": ["peanuts"],
        "cravings": ["chocolate", "umami"],
        "occasion": "wedding",
        "max_time": 9999,
    }
    req, unrecognized = ground(raw, matcher)
    assert req.pantry_ids() == {"eggs"}  # peanuts dropped: the user is allergic
    assert req.diets == ["vegan"] and req.cravings == ["chocolate"]
    assert req.occasion is None and req.max_time is None
    assert unrecognized == ["dragon fruit"]


def test_llm_mismapping_is_corrected_by_literal_match(matcher):
    llm = FakeLLM(lambda *_: json.dumps({"lang": "ar", "pantry": [{"name": "semolina"}, {"name": "rose_water"}], "occasion": "eid"}))
    req, _ = parse_with_llm(llm, "m", "عندي سميد وماء الزهر للعيد", matcher)
    assert req.pantry_ids() == {"semolina", "orange_blossom_water"}


def _result(expert: ExpertSystem, request: UserRequest):
    return expert.recommend(request)


def test_narration_verifier_rejects_invented_ingredients(expert, matcher):
    request = UserRequest(pantry=[{"id": "all_purpose_flour"}, {"id": "butter"}, {"id": "powdered_sugar"}, {"id": "lemon_extract"}], lang="en")
    result = _result(expert, request)
    assert verify("Make the Lemon Butter Cookies with your butter.", result, expert, matcher, request) == []
    assert verify("Add some pistachios on top!", result, expert, matcher, request)
    assert verify("A bright lemony cookie with a hint of orange.", result, expert, matcher, request) == []  # flavor words of a citrus recipe

    invented = narrate(FakeLLM(lambda *_: "Bake them and sprinkle pistachios."), "m", result, expert, matcher, request)
    assert invented.source == "template" and invented.violations
    clean = narrate(FakeLLM(lambda *_: "**Lemon Butter Cookies** are perfect: you have everything."), "m", result, expert, matcher, request)
    assert clean.source == "llm" and "**" not in clean.text
