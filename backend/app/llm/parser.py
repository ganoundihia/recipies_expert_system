"""LLM request parser: free text in any language -> validated, KB-grounded :class:`UserRequest`.

The model only *extracts*; every value it returns is validated against the controlled
vocabulary and every ingredient is re-mapped to a knowledge-base id by the deterministic
matcher. Anything that cannot be grounded is reported back instead of being guessed.
"""

from __future__ import annotations

import json
import typing

from app.kb.matcher import IngredientMatcher
from app.llm.client import ChatModel
from app.schemas import Allergen, Category, Cuisine, Diet, Flavor, Occasion, Skill, UserRequest

VOCABULARY = {
    "diets": typing.get_args(Diet),
    "avoid": typing.get_args(Allergen),
    "cravings": typing.get_args(Flavor),
    "categories": typing.get_args(Category),
    "cuisines": typing.get_args(Cuisine),
}

SYSTEM_PROMPT = """You convert a baking request (English, French, Algerian Arabic/Darija or Arabic) into JSON.
Return ONLY a JSON object with these keys:
- "lang": "en" | "fr" | "ar" (language of the user's message)
- "pantry": list of {{"name": ingredient id, "qty": number or null}} for ingredients the user HAS. Never include ingredients they lack, want to avoid, or are allergic to. qty is in grams for solids, ml for liquids, pieces for eggs/fruit; null if not stated.
- "diets": subset of {diets}
- "avoid": allergens to exclude, subset of {avoid}
- "cravings": flavors they want, subset of {cravings}
- "categories": subset of {categories}
- "cuisines": subset of {cuisines}
- "occasion": one of {occasions} or null
- "skill": one of {skills} or null
- "max_time": total minutes available, or null
- "servings": number of people, or null
- "unrecognized": ingredient names the user has that are not in the id list
Ingredient ids: {ingredients}
Use an id from the list whenever the ingredient matches (e.g. "oeufs" -> "eggs", "زبدة" -> "butter").
Only fill a field when the user explicitly says it. Never infer categories, cuisines, skill or cravings from context: leave them empty or null. Do not invent values."""


def build_system_prompt(matcher: IngredientMatcher) -> str:
    return SYSTEM_PROMPT.format(
        **{key: ", ".join(values) for key, values in VOCABULARY.items()},
        occasions=", ".join(typing.get_args(Occasion)),
        skills=", ".join(typing.get_args(Skill)),
        ingredients=", ".join(matcher.kb.ingredients),
    )


def parse_with_llm(client: ChatModel, model: str, text: str, matcher: IngredientMatcher) -> tuple[UserRequest, list[str]]:
    raw = client.chat_json(model, [{"role": "system", "content": build_system_prompt(matcher)}, {"role": "user", "content": text}], temperature=0)
    request, unrecognized = ground(raw, matcher)
    return reconcile(request, text, matcher), unrecognized


def reconcile(request: UserRequest, text: str, matcher: IngredientMatcher) -> UserRequest:
    """Cross-check the model's ingredients against the deterministic matcher.

    An ingredient the model returned that does not appear literally in the text is kept
    (the model may know a synonym we lack), unless the text names a different ingredient
    of the same category that the model left out: then the model mis-mapped it, and the
    literal match wins (e.g. "ماء الزهر" is orange blossom water, not rose water).
    """
    mentioned = dict(matcher.find_all(text))
    kept = {p.id for p in request.pantry}
    excluded = set(request.avoid)
    pantry = []
    for item in request.pantry:
        category = matcher.kb.ingredients[item.id].category
        if item.id not in mentioned:
            literal = next((m for m in mentioned if m not in kept and matcher.kb.ingredients[m].category == category and not excluded & set(matcher.kb.ingredients[m].allergens)), None)
            if literal:
                kept.add(literal)
                pantry.append(item.model_copy(update={"id": literal, "qty": mentioned[literal] or item.qty}))
                continue
        pantry.append(item)
    return request.model_copy(update={"pantry": pantry})


def ground(raw: dict, matcher: IngredientMatcher) -> tuple[UserRequest, list[str]]:
    """Validate the model output against the KB; returns the request and ungrounded names."""
    unrecognized = [str(name) for name in raw.get("unrecognized") or [] if str(name).strip()]
    pantry: dict[str, float | None] = {}
    for item in raw.get("pantry") or []:
        name = item.get("name") if isinstance(item, dict) else item
        if not name:
            continue
        ingredient = matcher.resolve(str(name))
        if ingredient is None:
            unrecognized.append(str(name))
            continue
        qty = item.get("qty") if isinstance(item, dict) else None
        pantry.setdefault(ingredient, float(qty) if isinstance(qty, int | float) and qty > 0 else None)

    def allowed(key: str) -> list[str]:
        return sorted({v for v in raw.get(key) or [] if v in VOCABULARY[key]})

    def single(key: str, values: tuple[str, ...]) -> str | None:
        return raw.get(key) if raw.get(key) in values else None

    def positive_int(key: str, low: int, high: int) -> int | None:
        value = raw.get(key)
        return int(value) if isinstance(value, int | float) and low <= value <= high else None

    request = UserRequest(
        pantry=[{"id": ing, "qty": qty} for ing, qty in pantry.items()],
        diets=allowed("diets"),
        avoid=allowed("avoid"),
        cravings=allowed("cravings"),
        categories=allowed("categories"),
        cuisines=allowed("cuisines"),
        occasion=single("occasion", typing.get_args(Occasion)),
        skill=single("skill", typing.get_args(Skill)),
        max_time=positive_int("max_time", 5, 1440),
        servings=positive_int("servings", 1, 200),
        lang=raw.get("lang") if raw.get("lang") in ("en", "fr", "ar") else "en",
    )
    # An allergen the user avoids can never sit in the pantry list, whatever the model said.
    forbidden = set(request.avoid)
    request.pantry = [p for p in request.pantry if not forbidden & set(matcher.kb.ingredients[p.id].allergens)]
    return request, sorted(set(unrecognized))


def dumps_compact(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
