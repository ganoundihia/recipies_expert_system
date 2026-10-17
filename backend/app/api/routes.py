"""Public API: recommendation (structured and natural language), proofs, what-if, planning, catalog."""

from __future__ import annotations

import json
import typing

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR
from app.db import TranslationRow
from app.engine.planner import plan_bakes
from app.kb.labels import label
from app.llm.narrator import template_answer
from app.llm.translator import translate_steps
from app.schemas import Allergen, AskRequest, Category, Cuisine, Diet, Flavor, Lang, Occasion, PlanRequest, ProveRequest, Skill, UserRequest, WhatIfRequest
from app.service import PantryChef

router = APIRouter(prefix="/api")
EVAL_RESULTS = BACKEND_DIR / "eval" / "results.json"


def chef(request: Request) -> PantryChef:
    return request.app.state.chef


def db(request: Request) -> Session:
    return request.app.state.sessions()


def _check_ingredients(c: PantryChef, ids: typing.Iterable[str]) -> None:
    unknown = sorted(set(ids) - set(c.kb.ingredients))
    if unknown:
        raise HTTPException(422, f"Unknown ingredient ids: {', '.join(unknown)}")


@router.get("/health")
def health(request: Request) -> dict:
    c = chef(request)
    return {
        "status": "ok",
        "llm": c.llm_enabled,
        "models": {"parse": c.settings.parse_model, "narrate": c.settings.narrate_model, "guard": c.settings.guard_model} if c.llm_enabled else None,
        "knowledge_base": {"ingredients": len(c.kb.ingredients), "recipes": len(c.kb.recipes), "rules": len(c.kb.rules), "substitutions": len(c.kb.substitutions)},
    }


@router.get("/meta")
def meta(request: Request, lang: Lang = "en") -> dict:
    """Controlled vocabulary and ingredient catalog for building the UI."""
    c = chef(request)
    vocab = {"diets": Diet, "allergens": Allergen, "flavors": Flavor, "categories": Category, "cuisines": Cuisine, "occasions": Occasion, "skills": Skill}
    return {
        **{key: [{"id": v, "label": label(v, lang)} for v in typing.get_args(kind)] for key, kind in vocab.items()},
        "difficulties": [{"id": d, "label": label(d, lang)} for d in ("easy", "medium", "hard")],
        "ingredients": [
            {"id": i.id, "name": i.name.get(lang), "category": i.category, "unit": i.unit, "allergens": i.allergens, "animal": i.animal}
            for i in sorted(c.kb.ingredients.values(), key=lambda i: i.name.get(lang))
            if not i.staple
        ],
        "llm": c.llm_enabled,
    }


@router.get("/recipes")
def list_recipes(request: Request, lang: Lang = "en") -> list[dict]:
    return [
        {"id": r.id, "name": r.name.get(lang), "category": r.category, "cuisine": r.cuisine, "flavors": r.flavors, "time_minutes": r.time_minutes, "difficulty": r.difficulty}
        for r in chef(request).kb.recipes.values()
    ]


@router.get("/recipes/{recipe_id}")
def get_recipe(request: Request, recipe_id: str, lang: Lang = "en", servings: int | None = None) -> dict:
    c = chef(request)
    recipe = c.kb.recipes.get(recipe_id)
    if recipe is None:
        raise HTTPException(404, "Recipe not found")
    scale = servings / recipe.servings if servings else 1.0
    steps, translated = recipe.steps, False
    if lang != "en" and c.client is not None:
        with db(request) as session:
            key = f"{recipe_id}:{lang}"
            cached = session.get(TranslationRow, key)
            if cached and len(cached.steps) == len(recipe.steps):
                steps, translated = cached.steps, True
            elif (result := translate_steps(c.client, c.settings.parse_model, recipe.steps, lang)) is not None:
                session.merge(TranslationRow(key=key, steps=result))
                session.commit()
                steps, translated = result, True
    ingredients = [
        {"id": item.id, "name": c.kb.ingredients[item.id].name.get(lang), "qty": round(item.qty * scale, 1), "unit": c.kb.ingredients[item.id].unit, "optional": item.optional}
        for item in recipe.ingredients
    ]
    return {
        "id": recipe.id,
        "name": recipe.name.get(lang),
        "names": recipe.name.model_dump(),
        "cuisine": recipe.cuisine,
        "category": recipe.category,
        "flavors": recipe.flavors,
        "time_minutes": recipe.time_minutes,
        "difficulty": recipe.difficulty,
        "servings": round(recipe.servings * scale),
        "ingredients": ingredients,
        "steps": steps,
        "steps_translated": translated,
    }


@router.post("/recommend")
def recommend(request: Request, body: UserRequest) -> dict:
    c = chef(request)
    _check_ingredients(c, body.pantry_ids())
    result = c.expert.recommend(body)
    return {"answer": template_answer(result, c.expert, body.lang), "result": result.model_dump()}


@router.post("/ask")
def ask(request: Request, body: AskRequest) -> dict:
    return chef(request).ask(body)


@router.post("/prove")
def prove(request: Request, body: ProveRequest) -> dict:
    c = chef(request)
    _check_ingredients(c, body.request.pantry_ids())
    if body.recipe_id not in c.kb.recipes:
        raise HTTPException(404, "Recipe not found")
    return c.expert.prove(body.request, body.recipe_id)


@router.post("/what-if")
def what_if(request: Request, body: WhatIfRequest) -> dict:
    c = chef(request)
    _check_ingredients(c, [*body.request.pantry_ids(), *body.add])
    return c.expert.what_if(body.request, body.add)


@router.post("/plan")
def plan(request: Request, body: PlanRequest) -> dict:
    c = chef(request)
    _check_ingredients(c, body.request.pantry_ids())
    return plan_bakes(c.expert, body.request, body.bakes, body.budget)


@router.get("/eval")
def evaluation() -> dict:
    if not EVAL_RESULTS.exists():
        raise HTTPException(404, "No evaluation has been run yet")
    return json.loads(EVAL_RESULTS.read_text(encoding="utf-8"))
