"""Google OAuth 2.0 (authorization code flow). Users never type a Google password into this app."""
import secrets
import time
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Integration
from app.utils.crypto import decrypt_json, encrypt_json

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = {
    "google_calendar": ["https://www.googleapis.com/auth/calendar.events",
                        "https://www.googleapis.com/auth/calendar.readonly"],
    "google_sheets": ["https://www.googleapis.com/auth/spreadsheets",
                      "https://www.googleapis.com/auth/drive.metadata.readonly"],
}
_pending_states: dict[str, tuple[int, str, float]] = {}  # state -> (user_id, provider, created)


class GoogleNotConfigured(Exception):
    pass


class GoogleNotConnected(Exception):
    pass


def build_auth_url(user_id: int, provider: str) -> str:
    s = get_settings()
    if not s.google_configured:
        raise GoogleNotConfigured()
    state = secrets.token_urlsafe(32)
    _pending_states[state] = (user_id, provider, time.time())
    params = {"client_id": s.google_client_id, "redirect_uri": s.google_redirect_uri, "response_type": "code",
              "scope": " ".join(SCOPES[provider]), "access_type": "offline", "prompt": "consent",
              "include_granted_scopes": "true", "state": state}
    return f"{AUTH_URL}?{urlencode(params)}"


def consume_state(state: str) -> tuple[int, str] | None:
    entry = _pending_states.pop(state, None)
    if not entry or time.time() - entry[2] > 600:
        return None
    return entry[0], entry[1]


async def exchange_code(db: Session, user_id: int, provider: str, code: str) -> Integration:
    s = get_settings()
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(TOKEN_URL, data={"code": code, "client_id": s.google_client_id,
                                          "client_secret": s.google_client_secret,
                                          "redirect_uri": s.google_redirect_uri, "grant_type": "authorization_code"})
    r.raise_for_status()
    tok = r.json()
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    integ = db.query(Integration).filter_by(user_id=user_id, provider=provider).first() or Integration(
        user_id=user_id, provider=provider, config={})
    if integ.encrypted_tokens and "refresh_token" not in tok:
        tok["refresh_token"] = decrypt_json(integ.encrypted_tokens).get("refresh_token")
    integ.encrypted_tokens = encrypt_json(tok)
    integ.status, integ.scopes = "CONNECTED", tok.get("scope", "")
    db.add(integ)
    db.commit()
    return integ


async def access_token(db: Session, user_id: int, provider: str) -> str:
    integ = db.query(Integration).filter_by(user_id=user_id, provider=provider, status="CONNECTED").first()
    if not integ or not integ.encrypted_tokens:
        raise GoogleNotConnected()
    tok = decrypt_json(integ.encrypted_tokens)
    if tok.get("expires_at", 0) > time.time():
        return tok["access_token"]
    if not tok.get("refresh_token"):
        integ.status = "EXPIRED"
        db.commit()
        raise GoogleNotConnected()
    s = get_settings()
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(TOKEN_URL, data={"client_id": s.google_client_id, "client_secret": s.google_client_secret,
                                          "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
    if r.status_code >= 400:
        integ.status = "EXPIRED"
        db.commit()
        raise GoogleNotConnected()
    new = r.json()
    tok.update(access_token=new["access_token"], expires_at=time.time() + new.get("expires_in", 3600) - 60)
    integ.encrypted_tokens = encrypt_json(tok)
    db.commit()
    return tok["access_token"]
