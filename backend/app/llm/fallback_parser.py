"""Deterministic keyword parser (EN/FR/AR). Used when no LLM is available, when the input is
flagged by the prompt guard, and as the 'rules only' baseline in the evaluation."""

from __future__ import annotations

import re

from app.kb.matcher import IngredientMatcher, canonical_text, normalize, tokenize
from app.schemas import UserRequest

DIET_KEYWORDS = {
    "vegan": ["vegan", "vegane", "vegetalien", "vegetalienne", "نباتي"],
    "gluten_free": ["gluten free", "gluten-free", "sans gluten", "بدون غلوتين", "خالي من الغلوتين", "celiac", "coeliaque"],
    "dairy_free": ["dairy free", "dairy-free", "lactose free", "sans lactose", "sans produits laitiers", "بدون حليب", "بدون لاكتوز"],
    "egg_free": ["egg free", "egg-free", "eggless", "sans oeuf", "sans oeufs", "بدون بيض"],
    "nut_free": ["nut free", "nut-free", "sans fruits a coque", "sans noix", "بدون مكسرات"],
}
ALLERGY_MARKERS = ["allergic to", "allergy to", "allergie", "allergique", "intolerant", "intolerance", "حساسية"]
NEGATIONS = {"no", "not", "without", "dont", "don", "sans", "pas", "plus", "بدون", "ما", "ماعنديش", "مكانش", "ماكانش"}
WANT_MARKERS = ["want", "craving", "crave", "feel like", "love", "like", "envie", "voudrais", "aimerais", "adore", "j aime", "something", "quelque chose", "نحب", "بغيت", "أريد", "اريد", "حاب"]
FLAVOR_KEYWORDS = {
    "chocolate": ["chocolate", "chocolatey", "chocolaty", "chocolat", "شوكولا", "شكولاطة", "شوكولاتة"],
    "vanilla": ["vanilla", "vanille", "فانيليا"],
    "coffee": ["coffee", "cafe", "mocha", "moka", "قهوة"],
    "citrus": ["lemon", "lemony", "citrus", "orange", "citron", "agrumes", "ليمون", "حمضيات"],
    "floral": ["floral", "orange blossom", "fleur d oranger", "rose", "ماء الزهر"],
    "nutty": ["nutty", "almond", "amande", "nuts", "noix", "لوز", "مكسرات"],
    "spice": ["spice", "spicy", "cinnamon", "epice", "cannelle", "قرفة"],
    "coconut": ["coconut", "coco", "جوز الهند"],
}
CATEGORY_KEYWORDS = {
    "cake": ["cake", "gateau", "كيك", "كعكة"],
    "cookie": ["cookie", "cookies", "biscuit", "biscuits", "sables", "gateaux secs", "بسكويت", "حلوة جافة"],
    "bread": ["bread", "brioche", "buns", "pain", "خبز"],
    "pastry": ["pastry", "pastries", "patisserie", "traditional", "traditionnel", "حلويات تقليدية"],
    "dessert": ["dessert", "crepe", "crepes", "تحلية"],
    "no_bake": ["no bake", "no-bake", "sans cuisson", "sans four", "بدون فرن"],
}
CUISINE_KEYWORDS = {
    "algerian": ["algerian", "algerien", "algerienne", "dziri", "جزائري", "جزائرية"],
    "french": ["french", "francais", "francaise", "فرنسي"],
    "mediterranean": ["mediterranean", "mediterraneen", "mediterraneenne", "متوسطي"],
}
OCCASION_KEYWORDS = [  # Order matters: "birthday" contains "عيد" in Arabic.
    ("birthday", ["birthday", "anniversaire", "عيد ميلاد"]),
    ("eid", ["eid", "aid", "laid", "العيد", "عيد"]),
    ("ramadan", ["ramadan", "رمضان"]),
    ("breakfast", ["breakfast", "petit dejeuner", "petit-dejeuner", "gouter", "فطور", "قهوة الصباح"]),
    ("kids", ["kids", "children", "child", "enfants", "enfant", "أطفال", "اطفال", "ولاد"]),
    ("guests", ["guests", "visitors", "invites", "ضيوف"]),
]
SKILL_KEYWORDS = {"beginner": ["beginner", "debutant", "debutante", "novice", "مبتدئ", "مبتدئة"], "expert": ["expert", "experienced", "confirme", "محترف"]}
FRENCH_HINTS = {"j", "ai", "je", "des", "du", "le", "la", "les", "et", "avec", "pour", "un", "une", "quelque", "chose", "veux", "farine", "oeufs"}


def _contains(text: str, keyword: str) -> bool:
    """Whole-word match on canonical forms, so plurals and Arabic clitics (للعيد -> عيد) still match."""
    return re.search(rf"(?<!\w){re.escape(canonical_text(keyword))}(?!\w)", text) is not None


def detect_lang(text: str) -> str:
    if re.search(r"[؀-ۿ]", text):
        return "ar"
    tokens = set(tokenize(text))
    return "fr" if len(tokens & FRENCH_HINTS) >= 2 else "en"


def parse_keywords(text: str, matcher: IngredientMatcher, lang: str | None = None) -> UserRequest:
    plain = normalize(text)
    norm = canonical_text(text)
    sentences = [s for s in re.split(r"[.!?;\n،؟]", plain) if s.strip()]
    diets = [d for d, words in DIET_KEYWORDS.items() if any(_contains(norm, w) for w in words)]
    occasion = next((o for o, words in OCCASION_KEYWORDS if any(_contains(norm, w) for w in words)), None)
    skill = next((s for s, words in SKILL_KEYWORDS.items() if any(_contains(norm, w) for w in words)), None)

    avoid: set[str] = set()
    pantry: dict[str, float | None] = {}
    cravings: set[str] = set()
    for sentence in sentences:
        canon = canonical_text(sentence)
        allergy = any(_contains(canon, marker) for marker in ALLERGY_MARKERS)
        wanting = any(_contains(canon, marker) for marker in WANT_MARKERS)
        tokens = tokenize(sentence)
        for ingredient, qty in matcher.find_all(sentence):
            ingredient_obj = matcher.kb.ingredients[ingredient]
            if allergy:
                avoid.update(ingredient_obj.allergens)
                continue
            if _negated(tokens, ingredient_obj):
                continue
            if wanting and ingredient_obj.flavors and not _possessive(canon):
                continue
            pantry.setdefault(ingredient, qty)
        if wanting:
            cravings.update(f for f, words in FLAVOR_KEYWORDS.items() if any(_contains(canon, w) for w in words))
        if allergy:
            for allergen, words in {
                "nuts": ["nuts", "noix", "fruits a coque"],
                "peanuts": ["peanut", "arachide"],
                "gluten": ["gluten"],
                "dairy": ["lactose", "dairy", "lait"],
                "egg": ["egg", "oeuf"],
                "sesame": ["sesame"],
            }.items():
                if any(_contains(canon, w) for w in words):
                    avoid.add(allergen)

    return UserRequest(
        pantry=[{"id": ing, "qty": qty} for ing, qty in pantry.items()],
        diets=diets,
        avoid=sorted(avoid),
        cravings=sorted(cravings),
        categories=[c for c, words in CATEGORY_KEYWORDS.items() if any(_contains(norm, w) for w in words)],
        cuisines=[c for c, words in CUISINE_KEYWORDS.items() if any(_contains(norm, w) for w in words)],
        occasion=occasion,
        skill=skill,
        max_time=_max_time(plain),
        servings=_servings(plain),
        lang=lang or detect_lang(text),
    )


def _possessive(sentence: str) -> bool:
    return any(_contains(sentence, w) for w in ["i have", "i ve got", "j ai", "il me reste", "عندي", "عندنا"])


def _negated(tokens: list[str], ingredient) -> bool:
    """True when a negation word appears just before a mention of the ingredient ("no eggs", "sans beurre")."""
    surfaces = {normalize(s) for s in (ingredient.name.en, ingredient.name.fr, ingredient.name.ar, *ingredient.aliases, ingredient.id.replace("_", " "))}
    heads = {surface.split()[0] for surface in surfaces if surface}
    return any((token in heads or token.rstrip("s") in heads) and NEGATIONS & set(tokens[max(0, index - 3) : index]) for index, token in enumerate(tokens))


def _max_time(text: str) -> int | None:
    if match := re.search(r"(\d+)\s*(?:min|mins|minutes|mn|دقيقة|دقائق)", text):
        return max(5, int(match.group(1)))
    if match := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:h|hour|hours|heure|heures|ساعة|ساعات)(?!\w)", text):
        return int(float(match.group(1).replace(",", ".")) * 60)
    return None


def _servings(text: str) -> int | None:
    match = re.search(r"(\d+)\s*(?:people|persons|guests|personnes|invites|اشخاص|أشخاص|شخص)", text)
    return int(match.group(1)) if match else None
