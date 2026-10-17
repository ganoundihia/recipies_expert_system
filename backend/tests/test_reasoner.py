from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.engine.mining import mine_pairing_rules, mine_substitutions
from app.engine.planner import plan_bakes
from app.kb.loader import load_seed_kb
from app.schemas import UserRequest

KB = load_seed_kb()


def request(*pantry, **kwargs) -> UserRequest:
    return UserRequest(pantry=[{"id": p} if isinstance(p, str) else {"id": p[0], "qty": p[1]} for p in pantry], **kwargs)


def uses(evaluation) -> set[str]:
    return {r.use for r in evaluation.resolutions if r.use} | {r.buy for r in evaluation.resolutions if r.buy}


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    pantry=st.lists(st.sampled_from(sorted(KB.ingredients)), max_size=15, unique=True),
    diets=st.lists(st.sampled_from(["vegan", "gluten_free", "dairy_free", "egg_free", "nut_free"]), max_size=2, unique=True),
    avoid=st.lists(st.sampled_from(["gluten", "dairy", "egg", "nuts", "peanuts", "sesame"]), max_size=2, unique=True),
)
def test_no_recommendation_ever_uses_a_forbidden_ingredient(expert, pantry, diets, avoid):
    """Safety property: whatever the pantry and constraints, the engine never proposes a forbidden ingredient."""
    req = UserRequest(pantry=[{"id": p} for p in pantry], diets=diets, avoid=avoid, top_k=30)
    result = expert.recommend(req)
    banned_allergens = set(avoid)
    for diet, allergen in (("gluten_free", "gluten"), ("dairy_free", "dairy"), ("egg_free", "egg"), ("nut_free", "nuts"), ("nut_free", "peanuts")):
        if diet in diets:
            banned_allergens.add(allergen)
    for evaluation in result.recommendations:
        for ingredient in uses(evaluation):
            item = KB.ingredients[ingredient]
            assert not banned_allergens & set(item.allergens), (evaluation.recipe_id, ingredient)
            assert not ("vegan" in diets and item.animal), (evaluation.recipe_id, ingredient)
        assert all(r.status != "impossible" for r in evaluation.resolutions)


def test_vegan_request_substitutes_or_excludes(expert):
    req = request("all_purpose_flour", "sugar", "vegetable_oil", "plant_milk", "flax_seeds", diets=["vegan"])
    memory = expert.infer(req)
    assert expert.evaluate(KB.recipes["vegan_chocolate_cake"], req, memory).feasible
    cupcakes = expert.evaluate(KB.recipes["vanilla_butter_cupcakes"], req, memory)
    assert cupcakes.feasible and {r.use for r in cupcakes.substitutions} >= {"flax_seeds", "plant_milk"}
    cheesecake = expert.evaluate(KB.recipes["basque_cheesecake"], req, memory)
    assert not cheesecake.feasible  # cream cheese has no vegan substitute


def test_substitution_used_when_substitute_is_in_pantry(expert):
    result = expert.recommend(request("all_purpose_flour", "margarine", "powdered_sugar", "lemon_extract", top_k=30))
    cookies = next(e for e in result.recommendations if e.recipe_id == "lemon_butter_cookies")
    assert cookies.makeable_now
    assert [r.substitution for r in cookies.substitutions] == ["butter_to_margarine"]


def test_partial_quantities_and_scaling(expert):
    recipe = KB.recipes["fudgy_brownies"]
    memory = expert.infer(request())
    evaluation = expert.evaluate(recipe, request(("eggs", 2), "dark_chocolate", "butter", "sugar", "all_purpose_flour", "cocoa_powder", servings=32), memory)
    eggs = next(r for r in evaluation.resolutions if r.ingredient == "eggs")
    assert eggs.need == 6 and eggs.status == "partial" and eggs.buy_qty == 4


def test_time_limit_excludes_long_recipes(expert):
    result = expert.recommend(request("bread_flour", "butter", "sugar", "milk", "eggs", "dry_yeast", max_time=60, top_k=30))
    assert all(e.time_minutes <= 60 for e in result.recommendations)


def test_preferences_drive_the_ranking(expert):
    pantry = ["all_purpose_flour", "sugar", "eggs", "butter", "milk", "baking_powder", "dark_chocolate", "cocoa_powder", "vanilla_extract"]
    top = expert.recommend(request(*pantry, cravings=["chocolate"])).recommendations[0]
    assert "chocolate" in KB.recipes[top.recipe_id].flavors


def test_beginner_eid_prefers_easy_algerian(expert):
    pantry = ["all_purpose_flour", "butter", "sugar", "eggs", "vegetable_oil", "powdered_sugar", "vanilla_sugar", "baking_powder"]
    top = expert.recommend(request(*pantry, occasion="eid", skill="beginner")).recommendations[0]
    assert KB.recipes[top.recipe_id].cuisine == "algerian" and top.difficulty == "easy"


def test_best_purchases_are_exact(expert):
    result = expert.recommend(request("all_purpose_flour", "butter", "sugar", "eggs", "milk", top_k=30))
    for suggestion in result.best_purchases:
        unlocked = expert.what_if(request("all_purpose_flour", "butter", "sugar", "eggs", "milk"), [suggestion.ingredient])
        assert set(suggestion.unlocks) <= set(unlocked["newly_makeable_ids"])


def test_proof_tree_statuses(expert):
    proof = expert.prove(request("all_purpose_flour", "margarine", "powdered_sugar"), "lemon_butter_cookies")
    assert proof["status"] == "needs_shopping"
    statuses = {child["goal"]: child["status"] for child in proof["children"]}
    assert statuses["obtain(Butter)"] == "substitute"
    assert statuses["obtain(Lemon or orange extract)"] == "buy"


def test_planner_respects_budget_and_reuses_leftovers(expert):
    plan = plan_bakes(expert, request("all_purpose_flour", "sugar", "eggs", "vegetable_oil"), bakes=3, budget=500)
    assert plan["total_cost"] <= 500
    assert len(plan["plan"]) == 3
    bought = {s["ingredient"] for s in plan["shopping_list"]}
    assert sum(len(p["buy"]) for p in plan["plan"]) >= len(bought)


def test_mining_finds_known_patterns(kb):
    subs = {(c["from"], c["to"]): c for c in mine_substitutions(kb)}
    assert ("vegetable_oil", "margarine") in subs and subs[("vegetable_oil", "margarine")]["kind"] == "substitution"
    assert ("vanilla_extract", "lemon_extract") in subs and subs[("vanilla_extract", "lemon_extract")]["kind"] == "variation"
    assert all(rule["lift"] > 1 for rule in mine_pairing_rules(kb))
