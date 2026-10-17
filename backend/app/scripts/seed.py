"""Seed (or reset) the database from the curated JSON knowledge base.

python -m app.scripts.seed           # create tables and seed if empty
python -m app.scripts.seed --reset   # drop everything (expert edits included) and reseed
"""

from __future__ import annotations

import argparse

from app.config import get_settings
from app.db import Base, init_db, make_engine, make_session_factory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    args = parser.parse_args()
    engine = make_engine(get_settings().database_url)
    if args.reset:
        Base.metadata.drop_all(engine)
    init_db(engine, make_session_factory(engine))
    print("Knowledge base ready.")


if __name__ == "__main__":
    main()
