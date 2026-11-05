"""Shared FastAPI dependencies: current user and ownership-checked lookups."""

from __future__ import annotations

import uuid
from typing import TypeVar

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import User, UserSession
from .security import SESSION_COOKIE, hash_token, is_expired

T = TypeVar("T")


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if session is None or is_expired(session.expires_at):
        return None
    return session.user


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "NOT_AUTHENTICATED", "message": "Log in to continue."})
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Admins only."})
    return user


def get_owned(db: Session, model: type[T], obj_id: uuid.UUID, user: User) -> T:
    """Fetch a row that belongs to the user, or 404.

    Another user's ID gives the same 404 as a missing one, so IDs can't be probed.
    """
    stmt = select(model).where(model.id == obj_id, model.user_id == user.id)  # type: ignore[attr-defined]
    if hasattr(model, "deleted_at"):
        stmt = stmt.where(model.deleted_at.is_(None))  # type: ignore[attr-defined]
    obj = db.scalar(stmt)
    if obj is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Not found."})
    return obj
