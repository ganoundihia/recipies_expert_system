"""Localized labels for the controlled vocabulary (allergens, flavors, categories...)."""

LABELS: dict[str, dict[str, str]] = {
    # Allergens
    "gluten": {"en": "gluten", "fr": "gluten", "ar": "الغلوتين"},
    "dairy": {"en": "dairy", "fr": "lactose", "ar": "مشتقات الحليب"},
    "egg": {"en": "eggs", "fr": "œufs", "ar": "البيض"},
    "nuts": {"en": "tree nuts", "fr": "fruits à coque", "ar": "المكسرات"},
    "peanuts": {"en": "peanuts", "fr": "arachides", "ar": "الفول السوداني"},
    "sesame": {"en": "sesame", "fr": "sésame", "ar": "السمسم"},
    # Flavors
    "vanilla": {"en": "vanilla", "fr": "vanille", "ar": "الفانيليا"},
    "chocolate": {"en": "chocolate", "fr": "chocolat", "ar": "الشوكولاتة"},
    "coffee": {"en": "coffee", "fr": "café", "ar": "القهوة"},
    "citrus": {"en": "citrus", "fr": "agrumes", "ar": "الحمضيات"},
    "floral": {"en": "floral", "fr": "floral", "ar": "الزهور"},
    "nutty": {"en": "nutty", "fr": "fruits secs", "ar": "المكسرات"},
    "spice": {"en": "spices", "fr": "épices", "ar": "التوابل"},
    "coconut": {"en": "coconut", "fr": "coco", "ar": "جوز الهند"},
    # Categories
    "cake": {"en": "cake", "fr": "gâteau", "ar": "كيك"},
    "cookie": {"en": "cookie", "fr": "biscuit", "ar": "بسكويت"},
    "bread": {"en": "sweet bread", "fr": "pain sucré", "ar": "خبز حلو"},
    "pastry": {"en": "pastry", "fr": "pâtisserie", "ar": "حلويات تقليدية"},
    "dessert": {"en": "dessert", "fr": "dessert", "ar": "تحلية"},
    "frosting": {"en": "frosting", "fr": "glaçage", "ar": "كريمة التزيين"},
    "no_bake": {"en": "no-bake treat", "fr": "douceur sans cuisson", "ar": "حلوى بدون فرن"},
    # Cuisines
    "algerian": {"en": "Algerian", "fr": "algérienne", "ar": "جزائري"},
    "french": {"en": "French", "fr": "française", "ar": "فرنسي"},
    "mediterranean": {"en": "Mediterranean", "fr": "méditerranéenne", "ar": "متوسطي"},
    "international": {"en": "international", "fr": "internationale", "ar": "عالمي"},
    # Difficulty
    "easy": {"en": "easy", "fr": "facile", "ar": "سهل"},
    "medium": {"en": "medium", "fr": "moyen", "ar": "متوسط"},
    "hard": {"en": "hard", "fr": "difficile", "ar": "صعب"},
}


def label(value: str, lang: str) -> str:
    entry = LABELS.get(value)
    return entry.get(lang, entry["en"]) if entry else value.replace("_", " ")
