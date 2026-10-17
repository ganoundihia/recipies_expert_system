"""Import baking recipes from the RecipeNLG dataset into the mining corpus.

RecipeNLG (https://recipenlg.cs.put.poznan.pl/) is distributed as ``full_dataset.csv`` after
accepting its terms. Only recipes whose title looks like a bake are kept, and only their
ingredient *ids* (mapped onto this knowledge base) are stored: they feed the knowledge mining
in the admin console, they are never shown to users.

    python -m app.scripts.import_recipenlg path/to/full_dataset.csv --limit 50000
"""

from __future__ import annotations

import argparse
import ast
import csv
import sys

from app.config import get_settings
from app.db import CorpusRecipe, init_db, make_engine, make_session_factory
from app.kb.loader import load_seed_kb
from app.kb.matcher import IngredientMatcher

CATEGORY_HINTS = {
    "cookie": ["cookie", "shortbread", "biscotti", "macaroon", "biscuit"],
    "cake": ["cake", "cupcake", "muffin", "brownie", "loaf", "madeleine", "financier"],
    "bread": ["bread", "brioche", "bun", "roll"],
    "pastry": ["baklava", "pastry", "tart", "pie"],
    "dessert": ["crepe", "pancake", "pudding", "cheesecake"],
}


def category_of(title: str) -> str | None:
    lowered = title.lower()
    return next((category for category, words in CATEGORY_HINTS.items() if any(w in lowered for w in words)), None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path")
    parser.add_argument("--limit", type=int, default=50_000, help="maximum recipes to import")
    parser.add_argument("--min-ingredients", type=int, default=3)
    args = parser.parse_args()

    csv.field_size_limit(sys.maxsize if sys.maxsize < 2**31 else 2**31 - 1)
    matcher = IngredientMatcher(load_seed_kb())
    engine = make_engine(get_settings().database_url)
    sessions = make_session_factory(engine)
    init_db(engine, sessions)

    imported = scanned = 0
    batch: list[CorpusRecipe] = []
    with open(args.csv_path, encoding="utf-8", newline="") as handle, sessions() as session:
        for row in csv.DictReader(handle):
            scanned += 1
            category = category_of(row.get("title", ""))
            if category is None:
                continue
            try:
                names = ast.literal_eval(row.get("NER", "[]"))
            except (ValueError, SyntaxError):
                continue
            ids = sorted({i for name in names if (i := matcher.resolve(str(name), cutoff=0.9))})
            if len(ids) < args.min_ingredients:
                continue
            batch.append(CorpusRecipe(title=row["title"][:300], category=category, ingredients=ids))
            imported += 1
            if len(batch) >= 1000:
                session.add_all(batch)
                session.commit()
                batch.clear()
            if imported >= args.limit:
                break
        session.add_all(batch)
        session.commit()
    print(f"Scanned {scanned} recipes, imported {imported} baking recipes into the mining corpus.")


if __name__ == "__main__":
    main()
