from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..db_models import AuthToken, Resume, User, UserSession, utcnow
from ..deps import current_user
from ..mailer import get_mailer
from ..schemas import (
    DeleteAccountIn,
    EmailIn,
    LoginIn,
    Message,
    RegisterIn,
    ResetPasswordIn,
    TokenIn,
    UserOut,
)
from ..security import (
    SESSION_COOKIE,
    expires_in,
    hash_password,
    hash_token,
    is_expired,
    needs_rehash,
    new_token,
    password_problem,
    verify_password,
)
from ..settings import settings
from ..storage import get_storage

router = APIRouter(prefix="/auth", tags=["auth"])
account = APIRouter(prefix="/account", tags=["account"])


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role,
                   email_verified=user.email_verified_at is not None, created_at=user.created_at)


def _bad(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _start_session(db: Session, user: User, response: Response) -> None:
    token, token_hash = new_token()
    db.add(UserSession(user_id=user.id, token_hash=token_hash, expires_at=expires_in(days=settings.session_days)))
    db.commit()
    response.set_cookie(
        SESSION_COOKIE, token, max_age=settings.session_days * 86400, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )


def _issue_token(db: Session, user: User, purpose: str, hours: int) -> str:
    # Only the newest token of each purpose stays valid.
    db.execute(delete(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose,
                                       AuthToken.used_at.is_(None)))
    token, token_hash = new_token()
    db.add(AuthToken(user_id=user.id, purpose=purpose, token_hash=token_hash, expires_at=expires_in(hours=hours)))
    db.commit()
    return token


def _consume_token(db: Session, token: str, purpose: str) -> User:
    row = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(token), AuthToken.purpose == purpose))
    if row is None or row.used_at is not None or is_expired(row.expires_at):
        raise _bad(400, "INVALID_TOKEN", "This link is invalid or has expired. Request a new one.")
    row.used_at = utcnow()
    user = db.get(User, row.user_id)
    assert user is not None
    return user


def _send_verification(db: Session, user: User) -> None:
    token = _issue_token(db, user, "verify_email", hours=48)
    get_mailer().send(user.email, "Confirm your ResumeIQ email",
                      f"Confirm your email address:\n{settings.app_url}/verify-email?token={token}\n\n"
                      "The link expires in 48 hours.")


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    if problem := password_problem(body.password):
        raise _bad(422, "WEAK_PASSWORD", problem)
    if db.scalar(select(User).where(User.email == body.email)):
        raise _bad(409, "EMAIL_TAKEN", "An account with this email already exists. Log in instead.")
    user = User(email=body.email, password_hash=hash_password(body.password), full_name=body.full_name)
    db.add(user)
    db.commit()
    _send_verification(db, user)
    _start_session(db, user, response)
    return user_out(user)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not verify_password(user.password_hash if user else None, body.password) or user is None:
        raise _bad(401, "INVALID_CREDENTIALS", "The email or password is incorrect.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    _start_session(db, user, response)
    return user_out(user)


@router.post("/logout", response_model=Message)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Message:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(token)))
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return Message(message="Logged out.")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return user_out(user)


@router.post("/verify-email", response_model=UserOut)
def verify_email(body: TokenIn, db: Session = Depends(get_db)) -> UserOut:
    user = _consume_token(db, body.token, "verify_email")
    user.email_verified_at = user.email_verified_at or utcnow()
    db.commit()
    return user_out(user)


@router.post("/resend-verification", response_model=Message)
def resend_verification(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Message:
    if user.email_verified_at is None:
        _send_verification(db, user)
    return Message(message="If your email isn't confirmed yet, a new link is on its way.")


@router.post("/forgot-password", response_model=Message)
def forgot_password(body: EmailIn, db: Session = Depends(get_db)) -> Message:
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is not None:
        token = _issue_token(db, user, "reset_password", hours=1)
        get_mailer().send(user.email, "Reset your ResumeIQ password",
                          f"Choose a new password:\n{settings.app_url}/reset-password?token={token}\n\n"
                          "The link expires in 1 hour. If you didn't ask for this, ignore this email.")
    # Same answer either way, so this can't be used to find out who has an account.
    return Message(message="If an account exists for that email, a reset link is on its way.")


@router.post("/reset-password", response_model=Message)
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)) -> Message:
    if problem := password_problem(body.password):
        raise _bad(422, "WEAK_PASSWORD", problem)
    user = _consume_token(db, body.token, "reset_password")
    user.password_hash = hash_password(body.password)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))  # log out everywhere
    db.commit()
    return Message(message="Password changed. Log in with your new password.")


@account.delete("", response_model=Message)
def delete_account(body: DeleteAccountIn, response: Response, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> Message:
    """Permanently delete the account, every resume file, and all related data."""
    if not verify_password(user.password_hash, body.password):
        raise _bad(401, "INVALID_CREDENTIALS", "The password is incorrect.")
    storage = get_storage()
    for key in db.scalars(select(Resume.storage_key).where(Resume.user_id == user.id, Resume.storage_key.is_not(None))):
        storage.delete(key)
    db.delete(user)  # cascades to sessions, tokens, resumes, versions, jobs, analyses
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return Message(message="Your account and all its data have been deleted.")
