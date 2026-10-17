from app.kb.models import ALLERGENS, CATEGORIES, CUISINES, DIFFICULTIES, FLAVORS


def test_recipes_are_complete_and_consistent(kb):
    for recipe in kb.recipes.values():
        assert recipe.name.en and recipe.name.fr and recipe.name.ar, recipe.id
        assert recipe.category in CATEGORIES and recipe.cuisine in CUISINES and recipe.difficulty in DIFFICULTIES
        assert set(recipe.flavors) <= set(FLAVORS)
        assert len(recipe.steps) >= 4 and all(item.qty > 0 for item in recipe.ingredients)
        assert len({item.id for item in recipe.ingredients}) == len(recipe.ingredients), recipe.id


def test_ingredients_and_substitutions(kb):
    for ingredient in kb.ingredients.values():
        assert set(ingredient.allergens) <= set(ALLERGENS)
        assert ingredient.unit in ("g", "ml", "pc") and ingredient.pack > 0
    for sub in kb.substitutions:
        assert sub.from_ != sub.to and sub.ratio > 0


def test_every_rule_references_known_predicates(kb):
    produced = {rule.then[0] for rule in kb.rules}
    inputs = {"diet", "avoid", "craving", "want_category", "want_cuisine", "occasion", "skill", "allergen", "animal", "category"}
    for rule in kb.rules:
        for condition in rule.if_:
            assert condition[0] in produced | inputs, (rule.id, condition)
