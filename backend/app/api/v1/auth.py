import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update

from app.db.session import get_session
from app.models.student import (
    AuthSession,
    EmailVerificationToken,
    PasswordResetToken,
    StudentProfile,
    User,
)
from app.schemas.student import Credentials, EmailInput, Registration, ResetInput, TokenInput
from app.services.email import deliver
from app.services.security import (
    audit,
    authenticated,
    csrf_token,
    digest,
    dummy_hash,
    now,
    password_hasher,
    throttle,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
GENERIC = {
    "message": "If the address is eligible, check your inbox or local mail preview for the next step."
}


def public_user(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "email_verified": user.email_verified_at is not None,
    }


def send_token(request, db, user, kind):
    model = EmailVerificationToken if kind == "verification" else PasswordResetToken
    minutes = (
        request.app.state.settings.verification_minutes
        if kind == "verification"
        else request.app.state.settings.reset_minutes
    )
    db.execute(
        update(model)
        .where(model.user_id == user.id, model.consumed_at.is_(None))
        .values(consumed_at=now())
    )
    token = secrets.token_urlsafe(32)
    db.add(
        model(
            user_id=user.id, token_hash=digest(token), expires_at=now() + timedelta(minutes=minutes)
        )
    )
    try:
        settings = request.app.state.settings
        if settings.staging_demo:
            deliver(settings, user.email, kind, token, mailbox=request.app.state.staging_mailbox)
        else:
            deliver(settings, user.email, kind, token)
    except Exception as error:
        db.rollback()
        audit.error("event=mail_delivery_failed kind=%s error_type=%s", kind, type(error).__name__)
        raise HTTPException(503, "Email delivery is unavailable. Please try again.") from None


@router.post("/register", status_code=202)
def register(data: Registration, request: Request, db=Depends(get_session)):
    throttle(request, db, "register", data.email)
    encoded = password_hasher.hash(data.password)
    # PostgreSQL conflict handling keeps concurrent duplicate registrations generic.
    from sqlalchemy.dialects.postgresql import insert

    uid = uuid.uuid4()
    created = db.scalar(
        insert(User)
        .values(id=uid, email=data.email, password_hash=encoded, account_status="active")
        .on_conflict_do_nothing(index_elements=[User.email])
        .returning(User.id)
    )
    if created:
        user = db.get(User, uid)
        db.add(StudentProfile(user_id=uid))
        try:
            send_token(request, db, user, "verification")
        except HTTPException as error:
            if error.status_code != 503:
                raise
            return GENERIC
    db.commit()
    audit.info("event=registration_processed")
    return GENERIC


@router.post("/login")
def login(data: Credentials, request: Request, response: Response, db=Depends(get_session)):
    throttle(request, db, "login", data.email)
    user = db.scalar(select(User).where(User.email == data.email).with_for_update())
    valid = verify_password(user.password_hash if user else dummy_hash, data.password)
    if user is None or not valid or user.account_status != "active":
        audit.info("event=login_failed")
        raise HTTPException(401, "Invalid email or password.")
    settings = request.app.state.settings
    old_raw = request.cookies.get(settings.cookie_name, "")
    if old_raw:
        db.execute(
            update(AuthSession)
            .where(AuthSession.token_hash == digest(old_raw))
            .values(revoked_at=now())
        )
    raw = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=digest(raw),
            expires_at=now() + timedelta(hours=settings.session_hours),
        )
    )
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash(data.password)
    db.commit()
    response.set_cookie(
        settings.cookie_name,
        raw,
        max_age=settings.session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    audit.info("event=login_success")
    return {"user": public_user(user), "csrf_token": csrf_token(raw)}


@router.get("/me")
def me(request: Request, user=Depends(authenticated), db=Depends(get_session)):
    result = {
        "user": public_user(user),
        "csrf_token": csrf_token(request.cookies[request.app.state.settings.cookie_name]),
    }
    db.commit()
    return result


@router.post("/logout")
def logout(
    request: Request, response: Response, user=Depends(authenticated), db=Depends(get_session)
):
    request.state.auth_session.revoked_at = now()
    db.commit()
    response.delete_cookie(
        request.app.state.settings.cookie_name,
        path="/",
        secure=request.app.state.settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    audit.info("event=logout")
    return {"message": "Signed out."}


@router.post("/resend-verification", status_code=202)
def resend(data: EmailInput, request: Request, db=Depends(get_session)):
    throttle(request, db, "resend", data.email)
    user = db.scalar(select(User).where(User.email == data.email).with_for_update())
    if user and user.account_status == "active" and user.email_verified_at is None:
        try:
            send_token(request, db, user, "verification")
        except HTTPException as error:
            if error.status_code != 503:
                raise
            return GENERIC
    db.commit()
    return GENERIC


@router.post("/forgot-password", status_code=202)
def forgot(data: EmailInput, request: Request, db=Depends(get_session)):
    throttle(request, db, "forgot", data.email)
    user = db.scalar(select(User).where(User.email == data.email).with_for_update())
    if user and user.account_status == "active":
        try:
            send_token(request, db, user, "reset")
        except HTTPException as error:
            if error.status_code != 503:
                raise
            return GENERIC
    db.commit()
    return GENERIC


def consume(request, db, model, raw):
    throttle(request, db, "consume_" + model.__tablename__)
    token = db.scalar(select(model).where(model.token_hash == digest(raw)))
    if token is None:
        raise HTTPException(400, "This link is invalid or expired. Request a new one.")
    user = db.scalar(select(User).where(User.id == token.user_id).with_for_update())
    if user is None:
        raise HTTPException(400, "This link is invalid or expired. Request a new one.")
    db.refresh(token)
    if (
        not user
        or user.account_status != "active"
        or token.consumed_at
        or token.expires_at <= now()
    ):
        raise HTTPException(400, "This link is invalid or expired. Request a new one.")
    if (
        request.app.state.settings.staging_demo
        and user.email not in request.app.state.settings.staging_synthetic_emails
    ):
        raise HTTPException(403, "This account is unavailable in the synthetic demo.")
    token.consumed_at = now()
    return user


@router.post("/verify-email")
def verify(data: TokenInput, request: Request, db=Depends(get_session)):
    user = consume(request, db, EmailVerificationToken, data.token)
    user.email_verified_at = now()
    db.commit()
    audit.info("event=email_verified")
    return {"message": "Email verified. You can now sign in to your workspace."}


@router.post("/reset-password")
def reset(data: ResetInput, request: Request, db=Depends(get_session)):
    user = consume(request, db, PasswordResetToken, data.token)
    user.password_hash = password_hasher.hash(data.password)
    if request.app.state.settings.reset_revokes_sessions:
        db.execute(
            update(AuthSession).where(AuthSession.user_id == user.id).values(revoked_at=now())
        )
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.consumed_at.is_(None))
        .values(consumed_at=now())
    )
    db.commit()
    audit.info("event=password_reset")
    return {"message": "Password reset. Sign in with your new password."}


@router.get("/sessions")
def sessions(request: Request, user=Depends(authenticated), db=Depends(get_session)):
    rows = db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now(),
        )
        .order_by(AuthSession.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": str(s.id),
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "last_used_at": s.last_used_at,
            "current": s.id == request.state.auth_session.id,
        }
        for s in rows
    ]


@router.delete("/sessions/{session_id}")
def revoke(
    session_id: uuid.UUID,
    request: Request,
    response: Response,
    user=Depends(authenticated),
    db=Depends(get_session),
):
    session = db.scalar(
        select(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == user.id)
    )
    if session is None:
        raise HTTPException(404, "Session not found.")
    session.revoked_at = now()
    db.commit()
    if session.id == request.state.auth_session.id:
        response.delete_cookie(
            request.app.state.settings.cookie_name,
            path="/",
            secure=request.app.state.settings.cookie_secure,
            httponly=True,
            samesite="lax",
        )
    audit.info("event=session_revoked")
    return {"message": "Session revoked."}


@router.delete("/sessions")
def revoke_other_sessions(request: Request, user=Depends(authenticated), db=Depends(get_session)):
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.id != request.state.auth_session.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now())
    )
    db.commit()
    audit.info("event=other_sessions_revoked")
    return {"message": "Other sessions revoked."}
