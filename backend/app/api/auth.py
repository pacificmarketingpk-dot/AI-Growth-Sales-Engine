from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.auth.deps import COOKIE_NAME, get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.database.session import get_db
from app.models import User, UserSettings
from app.schemas.api import ChangePasswordIn, LoginIn, RegisterIn, UserOut
from app.services.audit import audit
from app.utils.rate_limit import auth_limiter, client_key

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(resp: Response, user: User) -> str:
    s = get_settings()
    token = create_access_token(user.id, user.token_version)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=s.environment == "production",
                    max_age=s.access_token_minutes * 60, path="/")
    return token


@router.get("/config")
def auth_config(db: Session = Depends(get_db)):
    has_users = db.query(User.id).first() is not None
    return {"registration_open": get_settings().allow_registration or not has_users, "has_users": has_users}


@router.post("/register", response_model=UserOut)
def register(data: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    auth_limiter.check("register:" + client_key(request))
    has_users = db.query(User.id).first() is not None
    if has_users and not get_settings().allow_registration:
        raise HTTPException(403, "Registration is closed.")
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(409, "An account with this email already exists.")
    user = User(email=data.email.lower(), password_hash=hash_password(data.password), name=data.name)
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id, notification_email=user.email))
    audit(db, user.id, "user.registered", "user", user.id)
    db.commit()
    _set_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut)
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    auth_limiter.check("login:" + client_key(request))
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.password_hash) or not user.is_active:
        raise HTTPException(401, "Email or password is incorrect.")
    _set_cookie(response, user)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(data: ChangePasswordIn, response: Response, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect.")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1  # sign out other sessions
    audit(db, user.id, "user.password_changed", "user", user.id)
    db.commit()
    _set_cookie(response, user)
    return {"ok": True}


@router.post("/revoke-sessions")
def revoke_sessions(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1
    db.commit()
    _set_cookie(response, user)
    return {"ok": True}


@router.post("/api-token")
def api_token(user: User = Depends(get_current_user)):
    """Bearer token for scripted API access. Revoked by 'Sign out all sessions'."""
    return {"token": create_access_token(user.id, user.token_version),
            "expires_in_minutes": get_settings().access_token_minutes}
