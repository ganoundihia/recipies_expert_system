"""Knowledge acquisition: mines candidate substitutions and flavor-pairing rules from recipe data.

Mined knowledge is never applied directly: candidates are stored as *pending* and a
human expert approves or rejects them in the admin console.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from itertools import combinations

from app.kb.models import KnowledgeBase

VARIATION_CATEGORIES = {"flavoring", "spice", "fruit"}


def recipe_signatures(kb: KnowledgeBase, corpus: Iterable[tuple[str, list[str]]] = ()) -> list[tuple[str, frozenset[str]]]:
    """(category, ingredient set) for every KB recipe plus an optional external corpus."""
    rows = [(r.category, frozenset(i.id for i in r.ingredients if not i.optional)) for r in kb.recipes.values()]
    rows += [(category, frozenset(ids)) for category, ids in corpus]
    return rows


def mine_substitutions(kb: KnowledgeBase, corpus: Iterable[tuple[str, list[str]]] = (), min_support: int = 1) -> list[dict]:
    """Two recipes of the same category that differ by exactly one ingredient suggest a swap.

    Recipes are bucketed by (category, ingredients minus one), which keeps this linear in the
    corpus size, so it also scales to large imported datasets.
    """
    buckets: dict[tuple[str, frozenset[str]], set[str]] = defaultdict(set)
    for category, ingredients in recipe_signatures(kb, corpus):
        for ingredient in ingredients:
            buckets[(category, ingredients - {ingredient})].add(ingredient)
    support: Counter[tuple[str, str]] = Counter()
    for swapped in buckets.values():
        for a, b in combinations(sorted(swapped), 2):
            support[(a, b)] += 1
            support[(b, a)] += 1
    existing = {(s.from_, s.to) for s in kb.substitutions}
    candidates = []
    for (a, b), count in support.most_common():
        ing_a, ing_b = kb.ingredients.get(a), kb.ingredients.get(b)
        if count < min_support or (a, b) in existing or not ing_a or not ing_b or ing_a.category != ing_b.category:
            continue
        kind = "variation" if ing_a.category in VARIATION_CATEGORIES else "substitution"
        candidates.append(
            {"id": f"mined_{a}_to_{b}", "from": a, "to": b, "ratio": 1.0, "cf": round(min(0.4 + 0.1 * count, 0.8), 2), "support": count, "kind": kind, "status": "pending", "source": "mined"}
        )
    return candidates


def mine_pairing_rules(kb: KnowledgeBase, min_support: int = 2) -> list[dict]:
    """Association rules between flavors (support, confidence, lift) turned into preference rules."""
    recipes = [set(r.flavors) for r in kb.recipes.values()]
    total = len(recipes)
    single = Counter(f for flavors in recipes for f in flavors)
    pairs = Counter(pair for flavors in recipes for pair in combinations(sorted(flavors), 2))
    existing = {(tuple(rule.if_[0]), tuple(rule.then)) for rule in kb.rules if len(rule.if_) == 1}
    rules = []
    for (x, y), count in pairs.items():
        if count < min_support:
            continue
        for a, b in ((x, y), (y, x)):
            confidence = count / single[a]
            lift = confidence / (single[b] / total)
            premise, conclusion = ("prefer_flavor", a), ("prefer_flavor", b)
            if lift <= 1.0 or (premise, conclusion) in existing:
                continue
            rules.append(
                {
                    "id": f"M_{a}_{b}",
                    "if": [list(premise)],
                    "then": list(conclusion),
                    "cf": round(min(confidence * 0.5, 0.5), 2),
                    "explain": {
                        "en": f"Recipes with {a} often also feature {b} (confidence {confidence:.0%}, lift {lift:.1f}).",
                        "fr": f"Les recettes {a} associent souvent {b} (confiance {confidence:.0%}, lift {lift:.1f}).",
                    },
                    "support": count,
                    "confidence": round(confidence, 3),
                    "lift": round(lift, 2),
                    "enabled": False,
                    "source": "mined",
                }
            )
    return sorted(rules, key=lambda r: (-r["lift"], -r["support"]))
