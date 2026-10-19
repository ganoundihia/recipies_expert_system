"""Grounded answer writing: the LLM phrases the engine's decision, then a verifier checks it.

The model receives only the facts the expert system produced. Its text is then scanned for
ingredient and recipe mentions; anything outside the allowed set (an invented ingredient,
another recipe) rejects the text and a deterministic template answer is used instead.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from app.engine.reasoner import Evaluation, ExpertSystem, Recommendation
from app.kb.matcher import IngredientMatcher, normalize
from app.llm.client import ChatModel, LLMError
from app.llm.parser import dumps_compact
from app.schemas import UserRequest

log = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "fr": "French", "ar": "Arabic"}

SYSTEM_PROMPT = """You are NeSyChef, a friendly baking assistant. A rule-based expert system has already chosen the recipes.
Write a short answer (3 to 6 sentences) in {language} that presents its top suggestion and mentions the alternatives.
Rules:
- Use ONLY the facts in the JSON. Never add ingredients, recipes, quantities or claims that are not there.
- Mention what is missing to buy and any substitution, exactly as given.
- If a "forbidden" list is present, reassure the user that those ingredients were excluded.
- No markdown headings, no lists, no emojis."""


class Narration(BaseModel):
    text: str
    source: str  # "llm" or "template"
    verified: bool
    violations: list[str] = []


def _facts(result: Recommendation, es: ExpertSystem, lang: str, limit: int = 3) -> dict:
    def describe(e: Evaluation) -> dict:
        return {
            "recipe": e.name,
            "match_percent": e.match_percent,
            "minutes": e.time_minutes,
            "difficulty": e.difficulty,
            "to_buy": [es.label(r.buy, lang) for r in e.missing],
            "substitutions": [{"replace": es.label(r.ingredient, lang), "with": es.label(r.use, lang), "how": r.note} for r in e.substitutions if r.use],
            "why": [ev.label for ev in e.evidence if ev.cf > 0][:3],
        }

    facts = {"recommendations": [describe(e) for e in result.recommendations[:limit]]}
    if result.forbidden:
        facts["forbidden"] = [es.label(i, lang) for i in result.forbidden][:8]
    return facts


def allowed_ingredients(result: Recommendation, es: ExpertSystem, request: UserRequest, matcher: IngredientMatcher, limit: int = 3) -> set[str]:
    """Ingredients the answer may mention: pantry, staples, the shown recipes and everything in the facts given to the model."""
    allowed = set(request.pantry_ids()) | set(result.forbidden) | {i.id for i in es.kb.ingredients.values() if i.staple}
    for evaluation in result.recommendations[:limit]:
        recipe = es.kb.recipes[evaluation.recipe_id]
        allowed |= {i.id for i in recipe.ingredients}
        allowed |= {r.use for r in evaluation.resolutions if r.use} | {r.buy for r in evaluation.resolutions if r.buy}
        # Substitution notes are part of the facts ("7 g flax + 45 ml water"), so what they name is grounded.
        for r in evaluation.substitutions:
            if r.note:
                allowed |= {ingredient for ingredient, _ in matcher.find_all(r.note)}
        # Naming a recipe's flavor ("coffee", "lemon", "chocolate") is not an invented ingredient.
        allowed |= {i.id for i in es.kb.ingredients.values() if set(i.flavors) & set(recipe.flavors)}
    return allowed


def verify(text: str, result: Recommendation, es: ExpertSystem, matcher: IngredientMatcher, request: UserRequest, limit: int = 3) -> list[str]:
    """Return the list of grounding violations found in the generated text."""
    violations = []
    allowed = allowed_ingredients(result, es, request, matcher, limit)
    shown = {e.recipe_id for e in result.recommendations[:limit]}
    norm = normalize(text)
    # Recipe names contain ingredient words ("Lemon Butter Cookies"): blank them out before scanning.
    scan = norm
    for recipe_id in shown:
        for name in es.kb.recipes[recipe_id].name.model_dump().values():
            if name:
                scan = scan.replace(normalize(name), " ")
    for ingredient, _ in matcher.find_all(scan):
        if ingredient not in allowed:
            violations.append(f"ingredient not in the selected recipes: {ingredient}")
    for recipe in es.kb.recipes.values():
        if recipe.id in shown:
            continue
        for name in (recipe.name.en, recipe.name.fr, recipe.name.ar):
            # Only distinctive names: short ones ("Crêpes") also occur inside other names.
            if name and len(name) >= 12 and normalize(name) in norm and not any(normalize(name) in normalize(es.kb.recipes[s].name.get(request.lang)) for s in shown):
                violations.append(f"recipe not recommended: {recipe.id}")
                break
    return violations


TEMPLATES = {
    "en": {
        "none": "I couldn't find a recipe that fits all your constraints. Try adding a few ingredients or relaxing a preference.",
        "top": "My top pick is {name} ({pct}% match, about {min} min).",
        "ready": "You already have everything for it.",
        "buy": "You'd need to buy: {items}.",
        "sub": "Swap {a} for {b}.",
        "alt": "Other good options: {names}.",
        "forbidden": "I excluded {items} as you asked.",
    },
    "fr": {
        "none": "Je n'ai trouvé aucune recette qui respecte toutes vos contraintes. Ajoutez quelques ingrédients ou assouplissez une préférence.",
        "top": "Ma suggestion : {name} ({pct} % de correspondance, environ {min} min).",
        "ready": "Vous avez déjà tout ce qu'il faut.",
        "buy": "Il vous faudra acheter : {items}.",
        "sub": "Remplacez {a} par {b}.",
        "alt": "Autres bonnes options : {names}.",
        "forbidden": "J'ai exclu {items} comme demandé.",
    },
    "ar": {
        "none": "لم أجد وصفة تحترم كل قيودك. جرّب إضافة بعض المكونات أو تخفيف أحد التفضيلات.",
        "top": "اقتراحي الأول: {name} (توافق {pct}٪، حوالي {min} دقيقة).",
        "ready": "لديك كل المكونات.",
        "buy": "ستحتاج إلى شراء: {items}.",
        "sub": "استبدل {a} بـ {b}.",
        "alt": "خيارات أخرى جيدة: {names}.",
        "forbidden": "استبعدت {items} كما طلبت.",
    },
}


def template_answer(result: Recommendation, es: ExpertSystem, lang: str) -> str:
    t = TEMPLATES.get(lang, TEMPLATES["en"])
    if not result.recommendations:
        return t["none"]
    top = result.recommendations[0]
    parts = [t["top"].format(name=top.name, pct=top.match_percent, min=top.time_minutes)]
    parts.append(t["buy"].format(items=", ".join(es.label(r.buy, lang) for r in top.missing)) if top.missing else t["ready"])
    parts += [t["sub"].format(a=es.label(r.ingredient, lang), b=es.label(r.use, lang)) for r in top.substitutions if r.use and not r.buy]
    if len(result.recommendations) > 1:
        parts.append(t["alt"].format(names=", ".join(e.name for e in result.recommendations[1:3])))
    if result.forbidden:
        parts.append(t["forbidden"].format(items=", ".join(es.label(i, lang) for i in result.forbidden[:5])))
    return " ".join(parts)


def narrate(client: ChatModel | None, model: str, result: Recommendation, es: ExpertSystem, matcher: IngredientMatcher, request: UserRequest) -> Narration:
    lang = request.lang
    fallback = Narration(text=template_answer(result, es, lang), source="template", verified=True)
    if client is None or not result.recommendations:
        return fallback
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(language=LANGUAGE_NAMES[lang])},
        {"role": "user", "content": dumps_compact(_facts(result, es, lang))},
    ]
    try:
        text = client.chat(model, messages, temperature=0.4, max_tokens=1200).replace("**", "").replace("__", "").strip()
    except LLMError as error:
        log.warning("Narration failed, using template: %s", error)
        return fallback
    violations = verify(text, result, es, matcher, request)
    if violations or not text:
        log.warning("Narration rejected by verifier: %s", violations)
        return fallback.model_copy(update={"violations": violations})
    return Narration(text=text, source="llm", verified=True)
