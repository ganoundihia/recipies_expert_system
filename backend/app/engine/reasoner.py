"""The expert system: evaluates every recipe against the user's pantry, constraints and preferences.

Pipeline for one request:

1. **Forward chaining** over the rule base turns the request into derived facts
   (forbidden ingredients, preferred flavors/categories/cuisines/difficulty, each with a CF).
2. **Goal-driven resolution** (backward chaining) proves ``can_make(recipe)`` by proving
   ``obtain(ingredient)`` for each ingredient: have it, substitute it, or buy it. Forbidden
   ingredients can only be obtained through an allowed substitute; otherwise the recipe is
   excluded. This makes constraint violations impossible by construction.
3. **Scoring** combines availability, substitution and preference evidence with MYCIN
   certainty-factor combination into a single score with a human-readable explanation.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel

from app.engine.inference import WorkingMemory, combine_all, forward_chain
from app.kb.labels import label as vocab_label
from app.kb.models import Ingredient, KnowledgeBase, Recipe, Substitution
from app.schemas import PantryItem, UserRequest

TEXT = {
    "missing": {"en": "Missing {n}: {names}", "fr": "Il manque {n} : {names}", "ar": "ينقص {n}: {names}"},
    "complete": {"en": "You have everything you need", "fr": "Vous avez tout ce qu'il faut", "ar": "لديك كل المكونات"},
    "substitute": {"en": "Substitute {a} with {b}", "fr": "Remplacer {a} par {b}", "ar": "استبدال {a} بـ {b}"},
    "flavor": {"en": "Matches your taste for {x}", "fr": "Correspond à votre envie : {x}", "ar": "يوافق ذوقك: {x}"},
    "fits": {"en": "{kind} '{x}' fits your request", "fr": "{kind} « {x} » correspond à votre demande", "ar": "{kind} '{x}' يناسب طلبك"},
    "no_match": {"en": "Doesn't match what you asked for", "fr": "Ne correspond pas à vos envies", "ar": "لا يوافق طلبك"},
    "against": {"en": "{kind} '{x}' goes against your request", "fr": "{kind} « {x} » va à l'encontre de votre demande", "ar": "{kind} '{x}' لا يناسب طلبك"},
    "forbidden": {
        "en": "Needs {names}, which your constraints forbid, and no allowed substitute exists.",
        "fr": "Nécessite {names}, interdit par vos contraintes, sans substitut autorisé.",
        "ar": "تحتاج {names}، وهو ممنوع حسب قيودك ولا يوجد بديل مسموح.",
    },
    "too_long": {"en": "Takes {t} min, more than your {limit} min limit.", "fr": "Demande {t} min, plus que votre limite de {limit} min.", "ar": "تستغرق {t} دقيقة، أكثر من حدك {limit} دقيقة."},
}
KINDS = {
    "category": {"en": "Category", "fr": "Catégorie", "ar": "الصنف"},
    "cuisine": {"en": "Cuisine", "fr": "Cuisine", "ar": "المطبخ"},
    "difficulty": {"en": "Difficulty", "fr": "Difficulté", "ar": "الصعوبة"},
}


def t(key: str, lang: str, **values) -> str:
    return TEXT[key].get(lang, TEXT[key]["en"]).format(**values)


Status = Literal["have", "partial", "substitute", "buy", "staple", "skipped", "impossible"]


class Resolution(BaseModel):
    """How one recipe ingredient is obtained."""

    ingredient: str
    need: float
    status: Status
    use: str | None = None
    use_qty: float = 0
    buy: str | None = None
    buy_qty: float = 0
    substitution: str | None = None
    cf: float = 1.0
    note: str | None = None


class Evidence(BaseModel):
    label: str
    cf: float


class Evaluation(BaseModel):
    recipe_id: str
    name: str
    category: str
    cuisine: str
    difficulty: str
    time_minutes: int
    servings: int
    feasible: bool
    makeable_now: bool
    score: float
    match_percent: int
    missing: list[Resolution]
    substitutions: list[Resolution]
    resolutions: list[Resolution]
    evidence: list[Evidence]
    excluded_reason: str | None = None
    cost_to_complete: float = 0


class PurchaseSuggestion(BaseModel):
    ingredient: str
    name: str
    unlocks: list[str]
    cost: float


class TraceStep(BaseModel):
    rule: str
    text: str
    cf: float


class Recommendation(BaseModel):
    recommendations: list[Evaluation]
    excluded: list[Evaluation]
    trace: list[TraceStep]
    best_purchases: list[PurchaseSuggestion]
    forbidden: list[str]
    considered: int


def request_facts(request: UserRequest) -> list[tuple[str, ...]]:
    facts: list[tuple[str, ...]] = [("have", item.id) for item in request.pantry]
    facts += [("diet", diet) for diet in request.diets]
    facts += [("avoid", allergen) for allergen in request.avoid]
    facts += [("craving", flavor) for flavor in request.cravings]
    facts += [("want_category", category) for category in request.categories]
    facts += [("want_cuisine", cuisine) for cuisine in request.cuisines]
    if request.occasion:
        facts.append(("occasion", request.occasion))
    if request.skill:
        facts.append(("skill", request.skill))
    return facts


def pack_cost(ingredient: Ingredient, qty: float) -> float:
    """Cost of the packs needed to buy ``qty`` units of an ingredient."""
    if qty <= 0 or ingredient.staple:
        return 0.0
    packs = math.ceil(qty / ingredient.pack - 1e-9)
    return round(packs * ingredient.pack * ingredient.price, 2)


class ExpertSystem:
    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    # --- Inference -------------------------------------------------------
    def infer(self, request: UserRequest) -> WorkingMemory:
        return forward_chain(self.kb.ingredient_facts() + request_facts(request), self.kb.rules)

    def label(self, value: str, lang: str) -> str:
        ingredient = self.kb.ingredients.get(value)
        return ingredient.name.get(lang) if ingredient else vocab_label(value, lang)

    def trace(self, memory: WorkingMemory, lang: str) -> list[TraceStep]:
        rules = {rule.id: rule for rule in self.kb.rules}
        steps = []
        for firing in memory.firings:
            steps.append(TraceStep(rule=firing.rule_id, text=firing.explain(rules[firing.rule_id], lang, lambda v: self.label(v, lang)), cf=round(firing.cf, 2)))
        return steps

    # --- Backward chaining: obtain(ingredient) ------------------------------
    def _allowed(self, ingredient_id: str, memory: WorkingMemory) -> bool:
        return not memory.holds(("forbidden", ingredient_id))

    def _substitutes(self, ingredient_id: str, recipe: Recipe, need: float, memory: WorkingMemory) -> list[Substitution]:
        return [sub for sub in self.kb.subs_by_source.get(ingredient_id, []) if sub.applies_to(recipe, need) and self._allowed(sub.to, memory)]

    def resolve(self, recipe: Recipe, item_id: str, need: float, optional: bool, stock: dict[str, float], memory: WorkingMemory, lang: str) -> Resolution:
        ingredient = self.kb.ingredients[item_id]
        allowed = self._allowed(item_id, memory)
        if ingredient.staple and allowed:
            return Resolution(ingredient=item_id, need=need, status="staple", use=item_id, use_qty=need)
        if allowed and stock.get(item_id, 0) >= need - 1e-9:
            stock[item_id] -= need
            return Resolution(ingredient=item_id, need=need, status="have", use=item_id, use_qty=need)
        subs = self._substitutes(item_id, recipe, need, memory)
        for sub in subs:
            sub_need = need * sub.ratio
            if stock.get(sub.to, 0) >= sub_need - 1e-9 or self.kb.ingredients[sub.to].staple:
                stock[sub.to] = stock.get(sub.to, 0) - sub_need
                return Resolution(ingredient=item_id, need=need, status="substitute", use=sub.to, use_qty=sub_need, substitution=sub.id, cf=sub.cf, note=sub.note.get(lang) if sub.note else None)
        if optional:
            return Resolution(ingredient=item_id, need=need, status="skipped", cf=1.0)
        if allowed:
            available = max(stock.get(item_id, 0), 0)
            if available > 0:
                stock[item_id] = 0
                return Resolution(ingredient=item_id, need=need, status="partial", use=item_id, use_qty=available, buy=item_id, buy_qty=need - available)
            return Resolution(ingredient=item_id, need=need, status="buy", buy=item_id, buy_qty=need)
        if subs:
            sub = subs[0]
            return Resolution(
                ingredient=item_id,
                need=need,
                status="buy",
                use=sub.to,
                use_qty=need * sub.ratio,
                buy=sub.to,
                buy_qty=need * sub.ratio,
                substitution=sub.id,
                cf=sub.cf,
                note=sub.note.get(lang) if sub.note else None,
            )
        return Resolution(ingredient=item_id, need=need, status="impossible", cf=0.0)

    # --- Recipe evaluation ------------------------------------------------
    def evaluate(self, recipe: Recipe, request: UserRequest, memory: WorkingMemory) -> Evaluation:
        lang = request.lang
        scale = (request.servings / recipe.servings) if request.servings else 1.0
        stock = {item.id: (math.inf if item.qty is None else item.qty) for item in request.pantry}
        resolutions = [self.resolve(recipe, item.id, round(item.qty * scale, 2), item.optional, stock, memory, lang) for item in recipe.ingredients]

        excluded_reason = None
        impossible = [r for r in resolutions if r.status == "impossible"]
        if impossible:
            names = ", ".join(self.label(r.ingredient, lang) for r in impossible)
            excluded_reason = t("forbidden", lang, names=names)
        elif request.max_time and recipe.time_minutes > request.max_time:
            excluded_reason = t("too_long", lang, t=recipe.time_minutes, limit=request.max_time)

        missing = [r for r in resolutions if r.buy]
        substitutions = [r for r in resolutions if r.substitution]
        evidence = self._evidence(recipe, memory, missing, substitutions, lang)
        score = combine_all(e.cf for e in evidence) if not excluded_reason else -1.0
        cost = sum(pack_cost(self.kb.ingredients[r.buy], r.buy_qty) for r in missing)
        return Evaluation(
            recipe_id=recipe.id,
            name=recipe.name.get(lang),
            category=recipe.category,
            cuisine=recipe.cuisine,
            difficulty=recipe.difficulty,
            time_minutes=recipe.time_minutes,
            servings=round(recipe.servings * scale),
            feasible=excluded_reason is None,
            makeable_now=excluded_reason is None and not missing,
            score=round(score, 4),
            match_percent=round((score + 1) * 50),
            missing=missing,
            substitutions=substitutions,
            resolutions=resolutions,
            evidence=evidence,
            excluded_reason=excluded_reason,
            cost_to_complete=round(cost, 2),
        )

    def _evidence(self, recipe: Recipe, memory: WorkingMemory, missing: list[Resolution], substitutions: list[Resolution], lang: str) -> list[Evidence]:
        evidence: list[Evidence] = []
        if missing:
            names = ", ".join(self.label(r.buy, lang) for r in missing)
            evidence.append(Evidence(label=t("missing", lang, n=len(missing), names=names), cf=-min(0.25 * len(missing), 0.9)))
        else:
            evidence.append(Evidence(label=t("complete", lang), cf=0.6))
        for r in substitutions:
            evidence.append(Evidence(label=t("substitute", lang, a=self.label(r.ingredient, lang), b=self.label(r.use, lang)), cf=-round((1 - r.cf) * 0.5, 3)))
        matched_preference = False
        for flavor, cf in memory.values("prefer_flavor").items():
            if flavor in recipe.flavors:
                matched_preference |= cf > 0
                evidence.append(Evidence(label=t("flavor", lang, x=vocab_label(flavor, lang)), cf=round(cf * 0.7, 3)))
        for predicate, attribute, weight in (("prefer_category", recipe.category, 0.7), ("prefer_cuisine", recipe.cuisine, 0.6), ("prefer_difficulty", recipe.difficulty, 0.4)):
            cf = memory.values(predicate).get(attribute)
            if cf:
                matched_preference |= cf > 0 and predicate != "prefer_difficulty"
                kind = KINDS[predicate.removeprefix("prefer_")].get(lang, "")
                evidence.append(Evidence(label=t("fits" if cf > 0 else "against", lang, kind=kind, x=vocab_label(attribute, lang)), cf=round(cf * weight, 3)))
        wanted = any(cf > 0 for p in ("prefer_flavor", "prefer_category", "prefer_cuisine") for cf in memory.values(p).values())
        if wanted and not matched_preference:
            evidence.append(Evidence(label=t("no_match", lang), cf=-0.4))
        return evidence

    def recommend(self, request: UserRequest) -> Recommendation:
        memory = self.infer(request)
        evaluations = [self.evaluate(recipe, request, memory) for recipe in self.kb.recipes.values()]
        feasible = sorted((e for e in evaluations if e.feasible), key=lambda e: (-e.score, len(e.missing), e.time_minutes))
        excluded = [e for e in evaluations if not e.feasible]
        return Recommendation(
            recommendations=feasible[: request.top_k],
            excluded=excluded[:10],
            trace=self.trace(memory, request.lang),
            best_purchases=self.best_purchases(feasible, request.lang),
            forbidden=sorted(fact[1] for fact, cf in memory.query("forbidden", "?i") if cf >= 0.2),
            considered=len(evaluations),
        )

    def best_purchases(self, evaluations: list[Evaluation], lang: str, limit: int = 5) -> list[PurchaseSuggestion]:
        """Which single ingredient to buy to unlock the most recipes (exact: recipes missing exactly one item)."""
        unlocks: dict[str, list[str]] = {}
        for evaluation in evaluations:
            buys = {r.buy for r in evaluation.missing}
            if len(buys) == 1:
                unlocks.setdefault(buys.pop(), []).append(evaluation.recipe_id)
        suggestions = [
            PurchaseSuggestion(ingredient=ing, name=self.label(ing, lang), unlocks=recipes, cost=pack_cost(self.kb.ingredients[ing], self.kb.ingredients[ing].pack)) for ing, recipes in unlocks.items()
        ]
        return sorted(suggestions, key=lambda s: (-len(s.unlocks), s.cost))[:limit]

    def what_if(self, request: UserRequest, add: list[str]) -> dict:
        """Compare makeable recipes before and after adding ingredients to the pantry."""
        before = {e.recipe_id for e in self.recommend(request.model_copy(update={"top_k": 1000})).recommendations if e.makeable_now}
        extra = [PantryItem(id=ing) for ing in add if ing in self.kb.ingredients and ing not in request.pantry_ids()]
        richer = request.model_copy(update={"pantry": [*request.pantry, *extra], "top_k": 1000})
        after = {e.recipe_id for e in self.recommend(richer).recommendations if e.makeable_now}
        return {
            "added": [item.id for item in extra],
            "newly_makeable": [self.kb.recipes[r].name.get(request.lang) for r in sorted(after - before)],
            "newly_makeable_ids": sorted(after - before),
            "makeable_before": len(before),
            "makeable_after": len(after),
        }

    def prove(self, request: UserRequest, recipe_id: str) -> dict:
        """Backward-chaining proof tree for the goal can_make(recipe)."""
        recipe = self.kb.recipes[recipe_id]
        memory = self.infer(request)
        evaluation = self.evaluate(recipe, request, memory)
        lang = request.lang
        children = []
        for r in evaluation.resolutions:
            name = self.label(r.ingredient, lang)
            node = {"goal": f"obtain({name})", "status": r.status, "cf": r.cf, "children": []}
            if r.status in ("have", "staple"):
                node["children"].append({"goal": f"have({name})", "status": "proved"})
            elif r.status == "substitute":
                node["children"] += [
                    {"goal": f"substitute({name} → {self.label(r.use, lang)})", "status": "proved", "rule": r.substitution, "cf": r.cf, "note": r.note},
                    {"goal": f"have({self.label(r.use, lang)})", "status": "proved"},
                ]
            elif r.status in ("buy", "partial"):
                if r.status == "partial":
                    node["children"].append({"goal": f"have({name}) — {r.use_qty:g} of {r.need:g}", "status": "partial"})
                if r.substitution:
                    node["children"].append({"goal": f"forbidden({name}) → substitute with {self.label(r.buy, lang)}", "status": "proved", "rule": r.substitution})
                node["children"].append({"goal": f"buy({self.label(r.buy, lang)}, {r.buy_qty:g} {self.kb.ingredients[r.buy].unit})", "status": "action"})
            elif r.status == "skipped":
                node["children"].append({"goal": "optional — skipped", "status": "proved"})
            else:
                node["children"].append({"goal": f"forbidden({name}) and no allowed substitute", "status": "failed"})
            children.append(node)
        return {
            "goal": f"can_make({recipe.name.get(lang)})",
            "status": "proved" if evaluation.makeable_now else ("needs_shopping" if evaluation.feasible else "failed"),
            "children": children,
            "evaluation": evaluation.model_dump(),
        }
