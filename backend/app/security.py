"""Passwords, session tokens and single-use tokens.

- Passwords: Argon2id (argon2-cffi defaults).
- Sessions: a random 256-bit token in an HttpOnly cookie. Only its SHA-256
  hash is stored, so a database leak does not leak usable sessions.
- CSRF: cookies are SameSite=Lax, and every state-changing API request must
  carry the X-Requested-With header, which a cross-site form cannot set.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

SESSION_COOKIE = "riq_session"
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "ResumeIQ"
MIN_PASSWORD_LENGTH = 10

_hasher = PasswordHasher()
# A real hash to verify against when the email is unknown, so login timing
# doesn't reveal which emails have accounts.
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_token() -> tuple[str, str]:
    """(token for the client, hash for the database)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def expires_in(**kwargs) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**kwargs)


def is_expired(ts: datetime) -> bool:
    if ts.tzinfo is None:  # SQLite returns naive datetimes
        ts = ts.replace(tzinfo=timezone.utc)
    return ts <= datetime.now(timezone.utc)


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Use at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > 256:
        return "Use 256 characters or fewer."
    if password.lower() in {"password12", "password123", "1234567890", "qwertyuiop"}:
        return "This password is too common."
    return None
