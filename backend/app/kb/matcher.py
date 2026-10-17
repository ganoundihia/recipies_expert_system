"""Multilingual ingredient matcher: maps free text (EN/FR/AR) to knowledge-base ingredient ids."""

from __future__ import annotations

import difflib
import re
import unicodedata

from app.kb.models import KnowledgeBase

_ARABIC_DIACRITICS = re.compile(r"[ً-ٰٟـ]")
_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[^\W\d_]+", re.UNICODE)
_UNIT_FACTORS = {
    "g": 1,
    "gr": 1,
    "gram": 1,
    "grams": 1,
    "gramme": 1,
    "grammes": 1,
    "kg": 1000,
    "kilo": 1000,
    "ml": 1,
    "cl": 10,
    "l": 1000,
    "litre": 1000,
    "liter": 1000,
    "غ": 1,
    "غرام": 1,
    "كغ": 1000,
    "مل": 1,
    "لتر": 1000,
}
_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "a": 1,
    "an": 1,
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "واحد": 1,
    "اثنين": 2,
    "ثلاث": 3,
    "ثلاثة": 3,
    "أربع": 4,
    "اربع": 4,
    "خمس": 5,
}


def normalize(text: str) -> str:
    text = _ARABIC_DIACRITICS.sub("", text.lower())
    text = text.replace("œ", "oe").replace("’", "'").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not (unicodedata.combining(ch) and ord(ch) < 0x0600))


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text))


def canonical(token: str) -> str:
    """Canonical matching key: drops English/French plural 's' and Arabic clitics (و ف ب ل + ال)."""
    if "؀" <= token[:1] <= "ۿ":
        if len(token) > 4 and token.startswith("لل"):
            return token[2:]
        if len(token) > 3 and token[0] in "وفبل":
            token = token[1:]
        if len(token) > 3 and token.startswith("ال"):
            token = token[2:]
        return token
    return token[:-1] if len(token) > 3 and token.endswith("s") else token


class IngredientMatcher:
    """Longest-match lookup over every ingredient name and alias, in all languages."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb
        self.index: dict[tuple[str, ...], str] = {}
        for ing in kb.ingredients.values():
            surfaces = [ing.id.replace("_", " "), ing.name.en, ing.name.fr, ing.name.ar, *ing.aliases]
            for surface in surfaces:
                tokens = tuple(canonical(t) for t in tokenize(surface))
                if tokens:
                    self.index.setdefault(tokens, ing.id)
        self.max_len = max(len(key) for key in self.index)
        self._flat = {" ".join(key): value for key, value in self.index.items()}

    def find_all(self, text: str) -> list[tuple[str, float | None]]:
        """Return (ingredient_id, quantity_or_None) for each ingredient mentioned in the text."""
        tokens = tokenize(text)
        keys = [canonical(t) for t in tokens]
        found: dict[str, float | None] = {}
        i = 0
        while i < len(tokens):
            for size in range(min(self.max_len, len(tokens) - i), 0, -1):
                ingredient = self.index.get(tuple(keys[i : i + size]))
                if ingredient:
                    qty = self._quantity_before(tokens, i, ingredient)
                    if ingredient not in found or found[ingredient] is None:
                        found[ingredient] = qty
                    i += size
                    break
            else:
                i += 1
        return list(found.items())

    def _quantity_before(self, tokens: list[str], index: int, ingredient: str) -> float | None:
        unit = self.kb.ingredients[ingredient].unit
        window = tokens[max(0, index - 3) : index]
        factor = 1.0
        for token in reversed(window):
            if token in _UNIT_FACTORS and unit in ("g", "ml"):
                factor = _UNIT_FACTORS[token]
                continue
            if token in ("de", "d", "of", "من"):
                continue
            number = _parse_number(token)
            return number * factor if number is not None else None
        return None

    def resolve(self, name: str, cutoff: float = 0.85) -> str | None:
        """Map one ingredient name (or id) to an id, tolerating small spelling differences."""
        if name in self.kb.ingredients:
            return name
        key = " ".join(canonical(t) for t in tokenize(name))
        if key in self._flat:
            return self._flat[key]
        close = difflib.get_close_matches(key, self._flat.keys(), n=1, cutoff=cutoff)
        return self._flat[close[0]] if close else None


def _parse_number(token: str) -> float | None:
    if token in _NUMBER_WORDS:
        return float(_NUMBER_WORDS[token])
    try:
        return float(token.replace(",", "."))
    except ValueError:
        return None


def canonical_text(text: str) -> str:
    return " ".join(canonical(t) for t in tokenize(text))
