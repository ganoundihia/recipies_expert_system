"""Persistence: the knowledge base lives in the database so experts can edit it from the admin console.

SQLite by default; set DATABASE_URL to a PostgreSQL URL in production (see docker-compose.yml).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.kb.loader import build_kb, read_json
from app.kb.models import KnowledgeBase


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class IngredientRow(Base):
    __tablename__ = "ingredients"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class RecipeRow(Base):
    __tablename__ = "recipes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class RuleRow(Base):
    __tablename__ = "rules"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="approved")  # approved | pending | rejected
    source: Mapped[str] = mapped_column(String(16), default="curated")  # curated | mined | expert
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class SubstitutionRow(Base):
    __tablename__ = "substitutions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="approved")
    source: Mapped[str] = mapped_column(String(16), default="curated")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class CorpusRecipe(Base):
    """External recipes (e.g. RecipeNLG) used only for knowledge mining."""

    __tablename__ = "corpus_recipes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(32))
    ingredients: Mapped[list] = mapped_column(JSON)


class TranslationRow(Base):
    __tablename__ = "translations"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    steps: Mapped[list] = mapped_column(JSON)


class AuditRow(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    action: Mapped[str] = mapped_column(String(32))
    target: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text, default="")


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def init_db(engine: Engine, session_factory: sessionmaker[Session]) -> None:
    """Create tables and seed the curated knowledge base on first start."""
    Base.metadata.create_all(engine)
    with session_factory() as session:
        if session.scalar(select(IngredientRow.id).limit(1)) is not None:
            return
        session.add_all(IngredientRow(id=item["id"], data=item) for item in read_json("ingredients.json"))
        session.add_all(RecipeRow(id=item["id"], data=item) for item in read_json("recipes.json"))
        session.add_all(RuleRow(id=item["id"], data=item) for item in read_json("rules.json"))
        session.add_all(SubstitutionRow(id=item["id"], data=item) for item in read_json("substitutions.json"))
        session.add(AuditRow(action="seed", target="kb", detail="Curated knowledge base loaded"))
        session.commit()


def load_kb(session: Session, override: tuple[str, str, dict] | None = None) -> KnowledgeBase:
    """Build the live KB from approved rows. ``override`` = (kind, id, data) previews an edit."""
    rules = {row.id: row.data for row in session.scalars(select(RuleRow).where(RuleRow.status == "approved"))}
    subs = {row.id: row.data for row in session.scalars(select(SubstitutionRow).where(SubstitutionRow.status == "approved"))}
    if override:
        kind, item_id, data = override
        (rules if kind == "rules" else subs)[item_id] = data
    return build_kb(
        [row.data for row in session.scalars(select(IngredientRow))],
        [row.data for row in session.scalars(select(RecipeRow))],
        [{**data, "status": "approved"} for data in subs.values()],
        list(rules.values()),
    )


def audit(session: Session, action: str, target: str, detail: str = "") -> None:
    session.add(AuditRow(action=action, target=target, detail=detail))
