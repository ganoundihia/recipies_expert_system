"""Rule-based expert system that recommends a baking recipe.

The user picks one ingredient from each category (flour, fat, flavoring).
Those choices are asserted as facts in working memory, then a forward-chaining
inference engine fires production rules until no new fact can be derived:

1. Classification rules turn raw ingredients into culinary properties
   (e.g. ``Butter`` -> ``texture: rich``, ``Lemon/orange extract`` -> ``aroma: citrus``).
2. Recommendation rules combine those properties into a single recipe.

Usage (as called by the Node server)::

    python expert_system.py '{"flour": "cake_flour", "fat": "butter", "flavor": "vanilla"}'

The result is printed on stdout as JSON::

    {"recipe": "Vanilla_Cupcakes_butter", "trace": ["R-F2: ...", ...]}

On invalid input the script prints ``{"error": "..."}`` and exits with code 2.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

Fact = tuple[str, str]

# Ingredient options the user can choose from, per category.
CHOICES: dict[str, tuple[str, ...]] = {
    "flour": ("all_purpose_flour", "cake_flour", "semolina", "bread_flour"),
    "fat": ("butter", "margarine", "vegetable_oil"),
    "flavor": ("lemon_orange_extract", "coffee_extract", "vanilla"),
}


@dataclass(frozen=True)
class Rule:
    """A production rule: IF every condition holds THEN assert the conclusion."""

    name: str
    conditions: tuple[Fact, ...]
    conclusion: Fact
    explanation: str

    def describe(self) -> str:
        return f"{self.name}: {self.explanation}"


# --- Knowledge base -------------------------------------------------------

CLASSIFICATION_RULES: tuple[Rule, ...] = (
    # Flour -> crumb structure
    Rule("R-F1", (("flour", "all_purpose_flour"),), ("crumb", "versatile"),
         "all-purpose flour gives a versatile, everyday crumb"),
    Rule("R-F2", (("flour", "cake_flour"),), ("crumb", "tender"),
         "low-protein cake flour gives a soft, tender crumb"),
    Rule("R-F3", (("flour", "semolina"),), ("crumb", "grainy"),
         "semolina gives a golden, slightly grainy crumb"),
    Rule("R-F4", (("flour", "bread_flour"),), ("crumb", "chewy"),
         "high-protein bread flour gives a chewy, structured crumb"),
    # Fat -> texture
    Rule("R-T1", (("fat", "butter"),), ("texture", "rich"),
         "butter brings a rich flavor and a short, crisp texture"),
    Rule("R-T2", (("fat", "vegetable_oil"),), ("texture", "moist"),
         "oil stays liquid at room temperature and keeps bakes moist"),
    Rule("R-T3", (("fat", "margarine"),), ("texture", "dense"),
         "margarine creams well and gives a firm, dense texture"),
    # Flavoring -> aroma
    Rule("R-A1", (("flavor", "lemon_orange_extract"),), ("aroma", "citrus"),
         "lemon/orange extract gives a fresh citrus aroma"),
    Rule("R-A2", (("flavor", "coffee_extract"),), ("aroma", "coffee"),
         "coffee extract gives a roasted coffee aroma"),
    Rule("R-A3", (("flavor", "vanilla"),), ("aroma", "vanilla"),
         "vanilla extract gives a sweet vanilla aroma"),
)

# (crumb, texture, aroma) -> recipe name. Names are the keys used by the client.
_RECOMMENDATIONS: dict[tuple[str, str, str], str] = {
    ("versatile", "rich", "citrus"): "Lemon_butter_cookies",
    ("versatile", "rich", "vanilla"): "Vanilla_pound_cake",
    ("versatile", "rich", "coffee"): "Coffee_cake",
    ("versatile", "moist", "citrus"): "Lemon_Drizzle_Muffins",
    ("versatile", "moist", "vanilla"): "Simple_vanilla_cake",
    ("versatile", "moist", "coffee"): "Coffee_Flavored_Cupcakes",
    ("versatile", "dense", "citrus"): "Citrus_Shortbread_Cookies",
    ("versatile", "dense", "vanilla"): "Margarine_Frosting",
    ("versatile", "dense", "coffee"): "Coffee_Shortbread",
    ("tender", "rich", "citrus"): "Citrus_Madeleines",
    ("tender", "rich", "vanilla"): "Vanilla_Cupcakes_butter",
    ("tender", "rich", "coffee"): "Coffee_Cake",
    ("tender", "moist", "citrus"): "Citrus_Olive_Oil_Cake",
    ("tender", "moist", "vanilla"): "Vanilla_Cupcakes_oil",
    ("tender", "moist", "coffee"): "Coffee_Cupcakes",
    ("tender", "dense", "citrus"): "Citrus_Pound_Cake",
    ("tender", "dense", "vanilla"): "Vanilla_Pound_Cake",
    ("tender", "dense", "coffee"): "Coffee_Pound_Cake",
    ("grainy", "rich", "citrus"): "Semolina_Cookies",
    ("grainy", "rich", "vanilla"): "Semolina_Cake",
    ("grainy", "rich", "coffee"): "Semolina_Biscotti",
    ("grainy", "moist", "citrus"): "Semolina_Citrus_Cake",
    ("grainy", "moist", "vanilla"): "Semolina_Vanilla_Cake",
    ("grainy", "moist", "coffee"): "Semolina_Coffee_Cake",
    ("grainy", "dense", "citrus"): "Semolina_Lemon_Pound_Cake",
    ("grainy", "dense", "vanilla"): "Semolina_Vanilla_Pound_Cake",
    ("grainy", "dense", "coffee"): "Semolina_Coffee_Pound_Cake",
    ("chewy", "rich", "citrus"): "Lemon_Bread",
    ("chewy", "rich", "vanilla"): "Vanilla_Bread",
    ("chewy", "rich", "coffee"): "Coffee_Bread",
    ("chewy", "moist", "citrus"): "Citrus_Bread",
    ("chewy", "moist", "vanilla"): "Vanilla_Bread_oil",
    ("chewy", "moist", "coffee"): "Coffee_Bread_oil",
    ("chewy", "dense", "citrus"): "Lemon_Bread_margarine",
    ("chewy", "dense", "vanilla"): "Vanilla_Bread_margarine",
    ("chewy", "dense", "coffee"): "Coffee_Bread_margarine",
}

RECOMMENDATION_RULES: tuple[Rule, ...] = tuple(
    Rule(
        f"R-{index:02d}",
        (("crumb", crumb), ("texture", texture), ("aroma", aroma)),
        ("recipe", recipe),
        f"{crumb} crumb + {texture} texture + {aroma} aroma -> {recipe}",
    )
    for index, ((crumb, texture, aroma), recipe) in enumerate(_RECOMMENDATIONS.items(), start=1)
)

KNOWLEDGE_BASE: tuple[Rule, ...] = CLASSIFICATION_RULES + RECOMMENDATION_RULES


# --- Inference engine -----------------------------------------------------

def forward_chain(facts: set[Fact], rules: tuple[Rule, ...] = KNOWLEDGE_BASE) -> tuple[set[Fact], list[str]]:
    """Fire rules until a fixed point is reached; return the facts and the firing trace."""
    memory = set(facts)
    trace: list[str] = []
    fired = True
    while fired:
        fired = False
        for rule in rules:
            if rule.conclusion not in memory and all(c in memory for c in rule.conditions):
                memory.add(rule.conclusion)
                trace.append(rule.describe())
                fired = True
    return memory, trace


def validate(choices: dict) -> dict[str, str]:
    """Return the normalized choices or raise ``ValueError`` describing the problem."""
    if not isinstance(choices, dict):
        raise ValueError("Input must be a JSON object.")
    normalized = {}
    for category, allowed in CHOICES.items():
        value = choices.get(category)
        if value not in allowed:
            raise ValueError(f"Invalid {category!r}: {value!r}. Expected one of {list(allowed)}.")
        normalized[category] = value
    return normalized


def recommend(choices: dict) -> dict:
    """Run the expert system on the user's choices and return the recipe with its reasoning."""
    facts = set(validate(choices).items())
    memory, trace = forward_chain(facts)
    recipes = [value for (attribute, value) in memory if attribute == "recipe"]
    return {"recipe": recipes[0] if recipes else None, "trace": trace}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(json.dumps({"error": "Usage: expert_system.py '<json choices>'"}))
        return 2
    try:
        result = recommend(json.loads(argv[1]))
    except (json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
