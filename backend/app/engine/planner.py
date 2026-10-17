"""Baking planner: picks several recipes under a budget, reusing leftovers from packs already bought."""

from __future__ import annotations

import math

from app.engine.reasoner import ExpertSystem
from app.schemas import PantryItem, UserRequest


def _stock_request(request: UserRequest, stock: dict[str, float]) -> UserRequest:
    pantry = [PantryItem(id=ing, qty=None if math.isinf(qty) else max(qty, 0)) for ing, qty in stock.items() if qty > 0]
    return request.model_copy(update={"pantry": pantry})


def plan_bakes(es: ExpertSystem, request: UserRequest, bakes: int, budget: float | None) -> dict:
    kb, lang = es.kb, request.lang
    memory = es.infer(request)
    stock = {item.id: (math.inf if item.qty is None else item.qty) for item in request.pantry}
    packs_bought: dict[str, int] = {}
    chosen: list[dict] = []
    spent = 0.0

    for _ in range(bakes):
        best = None
        for recipe in kb.recipes.values():
            if any(c["recipe_id"] == recipe.id for c in chosen):
                continue
            evaluation = es.evaluate(recipe, _stock_request(request, stock), memory)
            if not evaluation.feasible:
                continue
            cost = evaluation.cost_to_complete
            if budget is not None and spent + cost > budget:
                continue
            repeats = sum(c["category"] == recipe.category for c in chosen)
            # Prefer good matches, cheap completions and some variety across the plan.
            utility = evaluation.score - 0.4 * (cost / max(budget or 2000, 1)) - 0.15 * repeats
            if best is None or utility > best[0]:
                best = (utility, recipe, evaluation)
        if best is None:
            break
        _, recipe, evaluation = best
        for r in evaluation.resolutions:
            if r.use and r.status in ("have", "substitute", "partial"):
                stock[r.use] = stock.get(r.use, 0) - r.use_qty
            if r.buy:
                ingredient = kb.ingredients[r.buy]
                packs = math.ceil(r.buy_qty / ingredient.pack - 1e-9)
                packs_bought[r.buy] = packs_bought.get(r.buy, 0) + packs
                stock[r.buy] = stock.get(r.buy, 0) + packs * ingredient.pack - r.buy_qty
        spent += evaluation.cost_to_complete
        chosen.append(
            {
                "recipe_id": recipe.id,
                "name": evaluation.name,
                "category": recipe.category,
                "score": evaluation.score,
                "match_percent": evaluation.match_percent,
                "cost": evaluation.cost_to_complete,
                "buy": [{"ingredient": r.buy, "name": es.label(r.buy, lang), "qty": round(r.buy_qty, 1), "unit": kb.ingredients[r.buy].unit} for r in evaluation.missing],
            }
        )

    shopping = []
    for ing, packs in sorted(packs_bought.items()):
        ingredient = kb.ingredients[ing]
        shopping.append(
            {"ingredient": ing, "name": ingredient.name.get(lang), "packs": packs, "pack_size": ingredient.pack, "unit": ingredient.unit, "cost": round(packs * ingredient.pack * ingredient.price, 2)}
        )
    leftovers = [{"ingredient": ing, "name": es.label(ing, lang), "qty": round(qty, 1), "unit": kb.ingredients[ing].unit} for ing, qty in stock.items() if ing in packs_bought and 0 < qty < math.inf]
    return {"plan": chosen, "shopping_list": shopping, "total_cost": round(sum(s["cost"] for s in shopping), 2), "budget": budget, "leftovers": leftovers, "currency": "DZD"}
