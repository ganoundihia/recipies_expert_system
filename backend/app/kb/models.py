"""Domain model of the knowledge base: ingredients, recipes, substitutions and rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

LANGS = ("en", "fr", "ar")
ALLERGENS = ("gluten", "dairy", "egg", "nuts", "peanuts", "sesame")
DIETS = ("vegan", "gluten_free", "dairy_free", "egg_free", "nut_free")
FLAVORS = ("vanilla", "chocolate", "coffee", "citrus", "floral", "nutty", "spice", "coconut")
CATEGORIES = ("cake", "cookie", "bread", "pastry", "dessert", "frosting", "no_bake")
CUISINES = ("algerian", "french", "mediterranean", "international")
OCCASIONS = ("eid", "ramadan", "birthday", "breakfast", "kids", "guests")
SKILLS = ("beginner", "intermediate", "expert")
DIFFICULTIES = ("easy", "medium", "hard")


class Localized(BaseModel):
    en: str
    fr: str = ""
    ar: str = ""

    def get(self, lang: str) -> str:
        return getattr(self, lang, "") or self.en


class Ingredient(BaseModel):
    id: str
    name: Localized
    aliases: list[str] = []
    category: str
    allergens: list[str] = []
    animal: bool = False
    unit: str
    price: float = Field(description="Price in DZD per unit")
    pack: float = Field(description="Smallest pack sold, in units")
    flavors: list[str] = []
    staple: bool = False


class RecipeIngredient(BaseModel):
    id: str
    qty: float
    optional: bool = False


class Recipe(BaseModel):
    id: str
    name: Localized
    cuisine: str
    category: str
    flavors: list[str] = []
    time_minutes: int
    difficulty: str
    servings: int
    ingredients: list[RecipeIngredient]
    steps: list[str]


class Substitution(BaseModel):
    id: str
    from_: str = Field(alias="from")
    to: str
    ratio: float
    cf: float = Field(ge=0, le=1)
    max_qty: float | None = None
    excluded_categories: list[str] = []
    note: Localized | None = None
    status: str = "approved"
    source: str = "curated"

    model_config = {"populate_by_name": True}

    def applies_to(self, recipe: Recipe, qty: float) -> bool:
        if recipe.category in self.excluded_categories:
            return False
        return self.max_qty is None or qty <= self.max_qty


class Rule(BaseModel):
    """Production rule. Patterns are tuples whose items starting with '?' are variables."""

    id: str
    if_: list[list[str]] = Field(alias="if")
    then: list[str]
    cf: float = Field(ge=-1, le=1)
    explain: Localized
    enabled: bool = True
    source: str = "curated"

    model_config = {"populate_by_name": True}


@dataclass
class KnowledgeBase:
    ingredients: dict[str, Ingredient]
    recipes: dict[str, Recipe]
    substitutions: list[Substitution]
    rules: list[Rule]
    subs_by_source: dict[str, list[Substitution]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.subs_by_source = {}
        for sub in self.substitutions:
            if sub.status == "approved":
                self.subs_by_source.setdefault(sub.from_, []).append(sub)
        for subs in self.subs_by_source.values():
            subs.sort(key=lambda s: -s.cf)

    def ingredient_facts(self) -> list[tuple[str, ...]]:
        """Static facts describing ingredients, asserted before each inference run."""
        facts: list[tuple[str, ...]] = []
        for ing in self.ingredients.values():
            facts.append(("category", ing.id, ing.category))
            facts.extend(("allergen", ing.id, allergen) for allergen in ing.allergens)
            if ing.animal:
                facts.append(("animal", ing.id))
        return facts
