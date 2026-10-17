"""Request and response models shared by the engine, the LLM layer and the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Lang = Literal["en", "fr", "ar"]
Diet = Literal["vegan", "gluten_free", "dairy_free", "egg_free", "nut_free"]
Allergen = Literal["gluten", "dairy", "egg", "nuts", "peanuts", "sesame"]
Flavor = Literal["vanilla", "chocolate", "coffee", "citrus", "floral", "nutty", "spice", "coconut"]
Category = Literal["cake", "cookie", "bread", "pastry", "dessert", "frosting", "no_bake"]
Cuisine = Literal["algerian", "french", "mediterranean", "international"]
Occasion = Literal["eid", "ramadan", "birthday", "breakfast", "kids", "guests"]
Skill = Literal["beginner", "intermediate", "expert"]


class PantryItem(BaseModel):
    id: str
    qty: float | None = Field(default=None, ge=0, description="Amount available in the ingredient's unit; null means plenty")


class UserRequest(BaseModel):
    pantry: list[PantryItem] = []
    diets: list[Diet] = []
    avoid: list[Allergen] = []
    cravings: list[Flavor] = []
    categories: list[Category] = []
    cuisines: list[Cuisine] = []
    occasion: Occasion | None = None
    skill: Skill | None = None
    max_time: int | None = Field(default=None, ge=5, le=1440)
    servings: int | None = Field(default=None, ge=1, le=200)
    lang: Lang = "en"
    top_k: int = Field(default=5, ge=1, le=30)

    def pantry_ids(self) -> set[str]:
        return {item.id for item in self.pantry}


class AskRequest(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    lang: Lang | None = None
    top_k: int = Field(default=5, ge=1, le=30)


class WhatIfRequest(BaseModel):
    request: UserRequest
    add: list[str] = Field(min_length=1, max_length=10)


class ProveRequest(BaseModel):
    request: UserRequest
    recipe_id: str


class PlanRequest(BaseModel):
    request: UserRequest
    bakes: int = Field(default=3, ge=1, le=14)
    budget: float | None = Field(default=None, ge=0, description="Maximum shopping budget in DZD")
