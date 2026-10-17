"""Loads the curated knowledge base shipped as JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from app.kb.models import Ingredient, KnowledgeBase, Recipe, Rule, Substitution

DATA_DIR = Path(__file__).parent / "data"


def read_json(name: str) -> list[dict]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def build_kb(ingredients: list[dict], recipes: list[dict], substitutions: list[dict], rules: list[dict]) -> KnowledgeBase:
    kb = KnowledgeBase(
        ingredients={item["id"]: Ingredient.model_validate(item) for item in ingredients},
        recipes={item["id"]: Recipe.model_validate(item) for item in recipes},
        substitutions=[Substitution.model_validate(item) for item in substitutions],
        rules=[Rule.model_validate(item) for item in rules],
    )
    validate_kb(kb)
    return kb


def load_seed_kb() -> KnowledgeBase:
    return build_kb(read_json("ingredients.json"), read_json("recipes.json"), read_json("substitutions.json"), read_json("rules.json"))


def validate_kb(kb: KnowledgeBase) -> None:
    """Fail fast on dangling references so a broken edit never reaches the engine."""
    for recipe in kb.recipes.values():
        for item in recipe.ingredients:
            if item.id not in kb.ingredients:
                raise ValueError(f"Recipe {recipe.id!r} uses unknown ingredient {item.id!r}")
    for sub in kb.substitutions:
        for ref in (sub.from_, sub.to):
            if ref not in kb.ingredients:
                raise ValueError(f"Substitution {sub.id!r} references unknown ingredient {ref!r}")
