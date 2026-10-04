from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database.session import get_db
from app.models import Prospect, User

COOKIE_NAME = "age_session"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Accepts the httpOnly session cookie (browser) or a Bearer token (API access)."""
    token = request.cookies.get(COOKIE_NAME)
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:]
    payload = decode_token(token) if token else None
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user = db.get(User, int(payload.get("sub", 0)))
    if not user or not user.is_active or payload.get("tv") != user.token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return user


def get_owned_prospect(prospect_id: int, db: Session, user: User) -> Prospect:
    p = db.get(Prospect, prospect_id)
    if not p or p.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prospect not found")
    return p
