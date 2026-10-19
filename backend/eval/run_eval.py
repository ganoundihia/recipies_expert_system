"""Benchmark: LLM only vs rules only vs hybrid on requests with known ground truth.

    python -m eval.run_eval --cases 40

Each case is a synthetic request (pantry, diets, allergies, cravings, occasion, time)
rendered as natural language in English, French or Arabic. Because the ground truth is
known, every system's top recommendation can be checked objectively.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.engine.benchmark import synthetic_requests
from app.engine.reasoner import ExpertSystem
from app.kb.loader import load_seed_kb
from app.kb.models import KnowledgeBase
from app.llm.client import LLMError, OpenAICompatibleClient
from app.llm.fallback_parser import parse_keywords
from app.llm.parser import dumps_compact
from app.schemas import AskRequest, UserRequest
from app.service import NeSyChef

OUT = Path(__file__).parent / "results.json"

PHRASES = {
    "intro": {"en": "I have {items}.", "fr": "J'ai {items}.", "ar": "عندي {items}."},
    "and": {"en": " and ", "fr": " et ", "ar": " و"},
    "diet": {
        "vegan": {"en": "I'm vegan.", "fr": "Je suis vegan.", "ar": "أنا نباتي."},
        "gluten_free": {"en": "It must be gluten-free.", "fr": "Il faut que ce soit sans gluten.", "ar": "لازم بدون غلوتين."},
        "dairy_free": {"en": "It has to be dairy-free.", "fr": "Ça doit être sans lactose.", "ar": "لازم بدون حليب."},
        "egg_free": {"en": "It must be egg-free.", "fr": "La recette doit être sans oeufs.", "ar": "لازم بدون بيض."},
        "nut_free": {"en": "It must be nut-free.", "fr": "Sans fruits à coque s'il vous plaît.", "ar": "لازم بدون مكسرات."},
    },
    "avoid": {"en": "My daughter is allergic to {x}.", "fr": "Ma fille est allergique {x}.", "ar": "بنتي عندها حساسية من {x}."},
    "allergen_words": {
        "gluten": {"en": "gluten", "fr": "au gluten", "ar": "الغلوتين"},
        "dairy": {"en": "milk", "fr": "au lait", "ar": "الحليب"},
        "egg": {"en": "eggs", "fr": "aux oeufs", "ar": "البيض"},
        "nuts": {"en": "nuts", "fr": "aux fruits à coque", "ar": "المكسرات"},
        "peanuts": {"en": "peanuts", "fr": "aux arachides", "ar": "الكاوكاو"},
        "sesame": {"en": "sesame", "fr": "au sésame", "ar": "الجلجلان"},
    },
    "craving": {"en": "I'd love something {x}.", "fr": "J'ai envie de quelque chose {x}.", "ar": "نحب حاجة {x}."},
    "flavor_words": {
        "chocolate": {"en": "chocolatey", "fr": "au chocolat", "ar": "بالشوكولاتة"},
        "vanilla": {"en": "with vanilla", "fr": "à la vanille", "ar": "بالفانيليا"},
        "citrus": {"en": "lemony", "fr": "au citron", "ar": "بالليمون"},
        "coffee": {"en": "with coffee", "fr": "au café", "ar": "بالقهوة"},
        "nutty": {"en": "nutty", "fr": "aux amandes", "ar": "باللوز"},
        "floral": {"en": "with orange blossom", "fr": "à la fleur d'oranger", "ar": "بماء الزهر"},
    },
    "occasion": {
        "eid": {"en": "It's for Eid.", "fr": "C'est pour l'Aïd.", "ar": "هذا للعيد."},
        "birthday": {"en": "It's for a birthday.", "fr": "C'est pour un anniversaire.", "ar": "هذا لعيد ميلاد."},
        "kids": {"en": "It's for my kids.", "fr": "C'est pour mes enfants.", "ar": "هذا لولادي الأطفال."},
        "breakfast": {"en": "It's for breakfast.", "fr": "C'est pour le petit-déjeuner.", "ar": "هذا للفطور."},
        "ramadan": {"en": "It's for Ramadan evenings.", "fr": "C'est pour les soirées de Ramadan.", "ar": "هذا لسهرات رمضان."},
        "guests": {"en": "We have guests coming.", "fr": "On attend des invités.", "ar": "عندنا ضيوف."},
    },
    "time": {"en": "I only have {t} minutes.", "fr": "J'ai seulement {t} minutes.", "ar": "عندي غير {t} دقيقة."},
}

LLM_ONLY_PROMPT = """You are a baking assistant. Choose the single best recipe from the catalog for the user's request.
Strictly respect diets and allergies. You may propose ingredient substitutions.
Catalog (recipe_id: ingredient ids | minutes):
{catalog}
Return JSON: {{"recipe_id": "...", "substitutions": [{{"from": "...", "to": "..."}}], "missing": [ingredient ids the user must buy], "answer": "one sentence for the user"}}"""


def render(request: UserRequest, kb: KnowledgeBase) -> str:
    lang = request.lang
    names = [kb.ingredients[p.id].name.get(lang).lower() for p in request.pantry]
    items = ", ".join(names[:-1]) + PHRASES["and"][lang] + names[-1] if len(names) > 1 else names[0]
    parts = [PHRASES["intro"][lang].format(items=items)]
    parts += [PHRASES["diet"][d][lang] for d in request.diets]
    parts += [PHRASES["avoid"][lang].format(x=PHRASES["allergen_words"][a][lang]) for a in request.avoid]
    parts += [PHRASES["craving"][lang].format(x=PHRASES["flavor_words"][f][lang]) for f in request.cravings]
    if request.occasion:
        parts.append(PHRASES["occasion"][request.occasion][lang])
    if request.max_time:
        parts.append(PHRASES["time"][lang].format(t=request.max_time))
    return " ".join(parts)


def forbidden_for(expert: ExpertSystem, truth: UserRequest) -> set[str]:
    memory = expert.infer(truth)
    return {fact[1] for fact, cf in memory.query("forbidden", "?i") if cf >= 0.2}


def f1(predicted: set[str], expected: set[str]) -> float:
    if not predicted and not expected:
        return 1.0
    tp = len(predicted & expected)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(expected) if expected else 0.0
    return 0.0 if tp == 0 else 2 * precision * recall / (precision + recall)


def judge_engine_answer(expert: ExpertSystem, truth: UserRequest, parsed: UserRequest, result) -> dict:
    """Score the engine's top pick against the ground truth (not against its own parse)."""
    kb = expert.kb
    forbidden = forbidden_for(expert, truth)
    have = truth.pantry_ids()
    top = result.recommendations[0] if result.recommendations else None
    # Ingredients the user is allergic to are deliberately dropped from the pantry, so they are not expected.
    expected_pantry = {i for i in have if not set(truth.avoid) & set(kb.ingredients[i].allergens)}
    record = {
        "recipe": top.recipe_id if top else None,
        "hallucinated": False,
        "pantry_f1": f1(parsed.pantry_ids(), expected_pantry),
        "constraint_recall": _constraint_recall(truth, parsed),
    }
    if top is None:
        record.update(violation=False, shopping_exact=None, craving_match=None)
        return record
    used = {r.use for r in top.resolutions if r.use} | {r.buy for r in top.resolutions if r.buy}
    actually_missing = {i for i in used if i not in have and not kb.ingredients[i].staple}
    claimed_missing = {r.buy for r in top.missing}
    record.update(
        violation=bool(used & forbidden),
        shopping_exact=claimed_missing == actually_missing,
        craving_match=(bool(set(truth.cravings) & set(kb.recipes[top.recipe_id].flavors)) if truth.cravings else None),
    )
    return record


DIET_ALLERGENS = {"gluten_free": {"gluten"}, "dairy_free": {"dairy"}, "egg_free": {"egg"}, "nut_free": {"nuts", "peanuts"}, "vegan": {"animal"}}


def _exclusions(request: UserRequest) -> set[str]:
    """What a request rules out, independent of wording: 'egg-free diet' and 'avoid eggs' are the same constraint."""
    return set(request.avoid).union(*(DIET_ALLERGENS[d] for d in request.diets))


def _constraint_recall(truth: UserRequest, parsed: UserRequest) -> float | None:
    expected = _exclusions(truth)
    if not expected:
        return None
    return len(expected & _exclusions(parsed)) / len(expected)


def run_llm_only(client, model: str, kb: KnowledgeBase, expert: ExpertSystem, text: str, truth: UserRequest) -> dict:
    catalog = "\n".join(f"{r.id}: {','.join(i.id for i in r.ingredients if not i.optional)} | {r.time_minutes}" for r in kb.recipes.values())
    data = client.chat_json(model, [{"role": "system", "content": LLM_ONLY_PROMPT.format(catalog=catalog)}, {"role": "user", "content": text}], temperature=0)
    recipe_id = data.get("recipe_id")
    record = {"recipe": recipe_id, "pantry_f1": None, "constraint_recall": None}
    if recipe_id not in kb.recipes:
        record.update(hallucinated=True, violation=False, shopping_exact=False, craving_match=False if truth.cravings else None)
        return record
    recipe = kb.recipes[recipe_id]
    swaps = {s.get("from"): s.get("to") for s in data.get("substitutions") or [] if isinstance(s, dict) and s.get("to") in kb.ingredients}
    used = {swaps.get(i.id, i.id) for i in recipe.ingredients if not i.optional}
    have = truth.pantry_ids()
    actually_missing = {i for i in used if i not in have and not kb.ingredients[i].staple}
    claimed_missing = {m for m in data.get("missing") or [] if isinstance(m, str)}
    record.update(
        hallucinated=False,
        violation=bool(used & forbidden_for(expert, truth)),
        shopping_exact=claimed_missing == actually_missing,
        craving_match=(bool(set(truth.cravings) & set(recipe.flavors)) if truth.cravings else None),
    )
    return record


def _timing(started: float, waited_before: float, client: OpenAICompatibleClient) -> dict:
    """Wall time minus rate-limit backoff: the latency a paid / unthrottled deployment would see."""
    throttle = (client.waited_s - waited_before) * 1000
    return {"latency_ms": (time.perf_counter() - started) * 1000 - throttle, "throttle_wait_ms": throttle}


def rate(records: list[dict], key: str) -> float | None:
    values = [r[key] for r in records if r.get(key) is not None]
    return round(sum(float(v) for v in values) / len(values), 4) if values else None


def summarize(records: list[dict]) -> dict:
    latencies = [r["latency_ms"] for r in records if "latency_ms" in r]
    return {
        "constraint_violation_rate": rate(records, "violation"),
        "hallucinated_recipe_rate": rate(records, "hallucinated"),
        "shopping_list_accuracy": rate(records, "shopping_exact"),
        "craving_match_rate": rate(records, "craving_match"),
        "pantry_f1": rate(records, "pantry_f1"),
        "constraint_recall": rate(records, "constraint_recall"),
        "ungrounded_text_caught_rate": rate(records, "narration_rejected"),
        "error_rate": round(sum(1 for r in records if r.get("error")) / len(records), 4),
        "latency_p50_ms": round(statistics.median(latencies)) if latencies else None,
        "latency_p95_ms": round(statistics.quantiles(latencies, n=20)[-1]) if len(latencies) >= 20 else (max(latencies) if latencies else None),
    }


METRICS = {
    "constraint_violation_rate": ("Diet / allergy violations", "Top pick uses an ingredient the user's diet or allergy forbids.", "lower", "percent"),
    "hallucinated_recipe_rate": ("Invented recipes", "Top pick is not a recipe from the catalog.", "lower", "percent"),
    "shopping_list_accuracy": ("Honest shopping list", "Declared missing ingredients exactly match what the user really lacks.", "higher", "percent"),
    "craving_match_rate": ("Craving satisfied", "When a flavor was asked for, the top pick has it.", "higher", "percent"),
    "pantry_f1": ("Pantry extraction F1", "Ingredients understood from the text vs. the true pantry.", "higher", "number"),
    "constraint_recall": ("Constraint recall", "Share of stated diets/allergies the parser captured.", "higher", "percent"),
    "ungrounded_text_caught_rate": ("Ungrounded LLM text caught", "Generated answers rejected by the verifier and replaced by a safe template.", "lower", "percent"),
    "error_rate": ("Errors", "Requests that failed for infrastructure reasons (free-tier rate limits, network) and are excluded from the other metrics.", "lower", "percent"),
    "latency_p50_ms": ("Latency p50", "Median end-to-end time per request.", "lower", "ms"),
    "latency_p95_ms": ("Latency p95", "95th percentile end-to-end time.", "lower", "ms"),
}


def _run_one(name: str, chef: NeSyChef, client: OpenAICompatibleClient, settings, kb: KnowledgeBase, expert: ExpertSystem, text: str, truth: UserRequest) -> dict:
    """Run one system on one case and judge it against the ground truth."""
    started, waited = time.perf_counter(), client.waited_s
    try:
        if name == "rules_only":  # Keyword parser + expert system, no LLM at all.
            parsed = parse_keywords(text, chef.matcher)
            return {**judge_engine_answer(expert, truth, parsed, expert.recommend(parsed)), **_timing(started, waited, client)}
        if name == "llm_only":  # The model picks from the full catalog itself.
            return {**run_llm_only(client, settings.narrate_model, kb, expert, text, truth), **_timing(started, waited, client)}
        # Hybrid: guard + LLM parsing + expert system + verified narration.
        out = chef.ask(AskRequest(text=text, lang=truth.lang))
        parsed = UserRequest.model_validate(out["request"])
        record = judge_engine_answer(expert, truth, parsed, expert.recommend(parsed))
        record["narration_rejected"] = out["answer"]["source"] == "template" and bool(out["answer"]["violations"])
        return {**record, **_timing(started, waited, client)}
    except LLMError as error:
        return {"error": str(error), **_timing(started, waited, client)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=40)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--systems", default="llm_only,rules_only,hybrid", help="comma-separated; others are kept from the previous results.json")
    parser.add_argument("--retry-errors", action="store_true", help="only re-run cases that previously failed (rate limits, network)")
    args = parser.parse_args()
    selected = [name for name in ("rules_only", "llm_only", "hybrid") if name in args.systems.split(",")]

    settings = get_settings()
    if not settings.llm_api_key:
        raise SystemExit("LLM_API_KEY is required to run the LLM and hybrid systems.")
    kb = load_seed_kb()
    expert = ExpertSystem(kb)
    client = OpenAICompatibleClient(settings.llm_base_url, settings.llm_api_key, timeout=90, max_retries=12)
    chef = NeSyChef(kb, settings, client)
    truths = synthetic_requests(kb, args.cases, seed=args.seed)
    previous = json.loads(OUT.read_text(encoding="utf-8"))["cases_detail"] if OUT.exists() else {}
    results: dict[str, list[dict]] = {name: previous.get(name, []) if args.retry_errors or name not in selected else [] for name in ("llm_only", "rules_only", "hybrid")}

    for index, truth in enumerate(truths, start=1):
        text = render(truth, kb)
        for name in selected:
            if args.retry_errors:
                if "error" in results[name][index - 1]:
                    results[name][index - 1] = _run_one(name, chef, client, settings, kb, expert, text, truth)
                    print(f"[{index}] retried {name}: {results[name][index - 1].get('recipe') or results[name][index - 1].get('error')}", flush=True)
            else:
                results[name].append(_run_one(name, chef, client, settings, kb, expert, text, truth))
        if not args.retry_errors:
            print(f"[{index}/{len(truths)}] {truth.lang} " + " | ".join(f"{k}: {results[k][-1].get('recipe')}" for k in selected), flush=True)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases": len(truths),
        "models": {"llm_only": settings.narrate_model, "parse": settings.parse_model, "narrate": settings.narrate_model, "guard": settings.guard_model},
        "system_labels": {"llm_only": "LLM only", "rules_only": "Rules only", "hybrid": "Hybrid (NeSyChef)"},
        "systems": {name: summarize(records) for name, records in results.items()},
        "metrics": {key: {"label": label, "description": desc, "better": better, "format": fmt} for key, (label, desc, better, fmt) in METRICS.items()},
        "notes": [
            "Cases are synthetic requests with known ground truth, rendered in English, French and Arabic (seeded, reproducible).",
            "LLM only receives the full catalog with ingredient lists and must respect diets itself; its declared substitutions are honored when judging.",
            "Rules only uses the deterministic keyword parser; hybrid uses the LLM for parsing and narration, the expert system for every decision.",
            "Shopping-list accuracy compares declared missing items with what the user truly lacks, so parsing mistakes are penalized.",
            "LLM only sends the whole catalog (about 3k tokens) per request, so on Groq's free tier part of its requests exhausted "
            "the rate limit even after retries; its metrics cover the requests that completed.",
            "Latencies exclude the backoff imposed by Groq's free-tier rate limits (measured and stored separately as throttle_wait_ms).",
        ],
        "cases_detail": {name: records for name, records in results.items()},
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(dumps_compact(report["systems"]))


if __name__ == "__main__":
    main()
