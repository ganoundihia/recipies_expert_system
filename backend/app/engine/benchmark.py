"""Deterministic synthetic requests, shared by the admin impact preview and the evaluation."""

from __future__ import annotations

import random

from app.kb.models import KnowledgeBase
from app.schemas import UserRequest

COMMON = ["all_purpose_flour", "sugar", "eggs", "butter", "milk", "vegetable_oil", "baking_powder", "vanilla_sugar", "semolina", "salt"]
DIETS = [None, None, None, "vegan", "gluten_free", "dairy_free", "egg_free", "nut_free"]
AVOID = [None, None, None, None, "peanuts", "sesame", "nuts", "dairy"]
FLAVORS = [None, "chocolate", "vanilla", "citrus", "coffee", "nutty", "floral"]
OCCASIONS = [None, None, "eid", "birthday", "kids", "breakfast", "ramadan", "guests"]
TIMES = [None, None, 30, 60, 90]


def synthetic_requests(kb: KnowledgeBase, count: int, seed: int = 7) -> list[UserRequest]:
    rng = random.Random(seed)
    others = sorted(i for i in kb.ingredients if i not in COMMON and not kb.ingredients[i].staple)
    requests = []
    for _ in range(count):
        pantry = rng.sample(COMMON, rng.randint(3, 7)) + rng.sample(others, rng.randint(1, 5))
        diet, avoid, flavor, occasion = rng.choice(DIETS), rng.choice(AVOID), rng.choice(FLAVORS), rng.choice(OCCASIONS)
        requests.append(
            UserRequest(
                pantry=[{"id": ing} for ing in dict.fromkeys(pantry)],
                diets=[diet] if diet else [],
                avoid=[avoid] if avoid else [],
                cravings=[flavor] if flavor else [],
                occasion=occasion,
                max_time=rng.choice(TIMES),
                lang=rng.choice(["en", "en", "fr", "fr", "ar"]),
            )
        )
    return requests
