"""Knowledge-engineering console API: edit rules and substitutions, mine candidates, preview impact."""

from __future__ import annotations

import json
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from app.db import AuditRow, CorpusRecipe, RuleRow, SubstitutionRow, audit, load_kb
from app.engine.benchmark import synthetic_requests
from app.engine.mining import mine_pairing_rules, mine_substitutions
from app.engine.reasoner import ExpertSystem
from app.kb.models import Rule, Substitution

Kind = Literal["rules", "substitutions"]
ROWS = {"rules": RuleRow, "substitutions": SubstitutionRow}
MODELS = {"rules": Rule, "substitutions": Substitution}


def require_admin(request: Request, x_admin_token: str = Header(default="")) -> None:
    settings = request.app.state.chef.settings
    if not settings.admin_enabled:
        raise HTTPException(403, "The knowledge console is disabled: set ADMIN_TOKEN to enable it.")
    expected = settings.admin_token
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(401, "Invalid admin token")


router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


class ItemUpdate(BaseModel):
    data: dict
    status: Literal["approved", "pending", "rejected"] = "approved"


class PreviewRequest(BaseModel):
    kind: Kind
    data: dict


def _validate(kind: Kind, data: dict) -> dict:
    try:
        return MODELS[kind].model_validate(data).model_dump(by_alias=True, exclude_none=True)
    except ValidationError as error:
        raise HTTPException(422, error.errors(include_url=False)) from error


def _reload(request: Request) -> None:
    with request.app.state.sessions() as session:
        request.app.state.chef.load(load_kb(session))


def _rows(session, kind: Kind) -> list[dict]:
    rows = session.scalars(select(ROWS[kind]).order_by(ROWS[kind].status.desc(), ROWS[kind].id))
    return [{"id": r.id, "status": r.status, "source": r.source, "updated_at": r.updated_at.isoformat(), "data": r.data} for r in rows]


@router.get("/{kind}")
def list_items(request: Request, kind: Kind) -> list[dict]:
    with request.app.state.sessions() as session:
        return _rows(session, kind)


@router.put("/{kind}/{item_id}")
def upsert_item(request: Request, kind: Kind, item_id: str, body: ItemUpdate) -> dict:
    data = _validate(kind, {**body.data, "id": item_id})
    with request.app.state.sessions() as session:
        row = session.get(ROWS[kind], item_id)
        if row is None:
            row = ROWS[kind](id=item_id, data=data, status=body.status, source="expert")
            session.add(row)
        else:
            row.data, row.status = data, body.status
        try:
            load_kb(session)  # Refuse edits that would break the knowledge base.
        except ValueError as error:
            session.rollback()
            raise HTTPException(422, str(error)) from error
        audit(session, f"{kind}:{body.status}", item_id, json.dumps(data, ensure_ascii=False)[:2000])
        session.commit()
    _reload(request)
    return {"id": item_id, "status": body.status}


@router.post("/{kind}/{item_id}/{decision}")
def decide(request: Request, kind: Kind, item_id: str, decision: Literal["approve", "reject"]) -> dict:
    status = "approved" if decision == "approve" else "rejected"
    with request.app.state.sessions() as session:
        row = session.get(ROWS[kind], item_id)
        if row is None:
            raise HTTPException(404, "Not found")
        row.status = status
        if kind == "rules" and status == "approved":
            row.data = {**row.data, "enabled": True}
        audit(session, f"{kind}:{status}", item_id)
        session.commit()
    _reload(request)
    return {"id": item_id, "status": status}


@router.delete("/{kind}/{item_id}")
def delete_item(request: Request, kind: Kind, item_id: str) -> dict:
    with request.app.state.sessions() as session:
        row = session.get(ROWS[kind], item_id)
        if row is None:
            raise HTTPException(404, "Not found")
        session.delete(row)
        audit(session, f"{kind}:deleted", item_id)
        session.commit()
    _reload(request)
    return {"deleted": item_id}


@router.post("/mine")
def mine(request: Request) -> dict:
    """Mine candidate knowledge from the KB recipes and any imported corpus; store new ones as pending."""
    kb = request.app.state.chef.kb
    added = {"rules": 0, "substitutions": 0}
    with request.app.state.sessions() as session:
        corpus = [(row.category, row.ingredients) for row in session.scalars(select(CorpusRecipe))]
        candidates = {"substitutions": mine_substitutions(kb, corpus), "rules": mine_pairing_rules(kb)}
        for kind, items in candidates.items():
            for item in items:
                if session.get(ROWS[kind], item["id"]) is None:
                    session.add(ROWS[kind](id=item["id"], data=item, status="pending", source="mined"))
                    added[kind] += 1
        audit(session, "mine", "kb", json.dumps(added))
        session.commit()
    return {"added": added, "corpus_recipes": len(corpus)}


@router.post("/preview")
def preview(request: Request, body: PreviewRequest) -> dict:
    """What would change if this rule or substitution were approved? Replays 60 benchmark requests."""
    data = _validate(body.kind, body.data)
    with request.app.state.sessions() as session:
        before = request.app.state.chef.kb
        try:
            after = load_kb(session, override=(body.kind, data["id"], {**data, "enabled": True}))
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
    old, new = ExpertSystem(before), ExpertSystem(after)
    changed, unlocked, lost, top_changes = 0, 0, 0, 0
    examples = []
    for req in synthetic_requests(before, 60):
        req = req.model_copy(update={"top_k": 1000})
        a = {e.recipe_id: e for e in old.recommend(req).recommendations}
        b = {e.recipe_id: e for e in new.recommend(req).recommendations}
        now_makeable = {r for r, e in b.items() if e.makeable_now} - {r for r, e in a.items() if e.makeable_now}
        no_longer = {r for r, e in a.items() if e.makeable_now} - {r for r, e in b.items() if e.makeable_now}
        top_a, top_b = next(iter(a), None), next(iter(b), None)
        changed += bool(now_makeable or no_longer or top_a != top_b)
        unlocked += len(now_makeable)
        lost += len(no_longer)
        top_changes += top_a != top_b
        if now_makeable and len(examples) < 5:
            examples.append({"pantry": [p.id for p in req.pantry], "newly_makeable": sorted(now_makeable)})
    return {"requests": 60, "requests_changed": changed, "top_pick_changed": top_changes, "recipes_unlocked": unlocked, "recipes_lost": lost, "examples": examples}


@router.get("/audit/log")
def audit_log(request: Request) -> list[dict]:
    with request.app.state.sessions() as session:
        rows = session.scalars(select(AuditRow).order_by(AuditRow.id.desc()).limit(100))
        return [{"at": r.at.isoformat(), "action": r.action, "target": r.target, "detail": r.detail} for r in rows]
