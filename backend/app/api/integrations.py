from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import get_settings
from app.database.session import get_db
from app.models import Integration, User
from app.providers.base import FUTURE_INTEGRATIONS, PROSPECTING_SOURCES, DiscoveryCriteria
from app.services.ai.factory import provider_status
from app.services.audit import audit
from app.services.google import oauth
from app.services.notifications import smtp_configured

router = APIRouter(prefix="/api", tags=["integrations"])
GOOGLE = {"google_calendar": "Google Calendar", "google_sheets": "Google Sheets"}


@router.get("/integrations")
def list_integrations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_settings()
    rows = {i.provider: i for i in db.query(Integration).filter_by(user_id=user.id)}
    items = []
    for key, label in GOOGLE.items():
        i = rows.get(key)
        status = i.status if i else "NOT_CONNECTED"
        items.append({"provider": key, "label": label, "category": "Google", "status": status,
                      "available": s.google_configured, "config": (i.config if i else {}),
                      "note": None if s.google_configured else
                      "Google OAuth is not set up. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to the server .env."})
    for f in FUTURE_INTEGRATIONS:
        items.append({**f, "status": "NOT_CONNECTED", "available": False, "config": {}})
    return {"integrations": items, "ai": provider_status(), "email_notifications_available": smtp_configured(),
            "prospect_sources": [{"key": src.key, "label": src.label, "configured": src.configured()}
                                 for src in PROSPECTING_SOURCES]}


@router.post("/integrations/{provider}/connect")
def connect(provider: str, user: User = Depends(get_current_user)):
    if provider in GOOGLE:
        try:
            return {"auth_url": oauth.build_auth_url(user.id, provider)}
        except oauth.GoogleNotConfigured:
            raise HTTPException(409, "Google OAuth is not set up on the server. Add GOOGLE_CLIENT_ID and "
                                     "GOOGLE_CLIENT_SECRET to .env, then restart.")
    raise HTTPException(409, "This integration isn't available yet. No connection was made.")


@router.get("/integrations/google/callback")
async def google_callback(code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    front = get_settings().frontend_url.rstrip("/") + "/settings?"
    entry = oauth.consume_state(state) if state else None
    if error or not code or not entry:
        return RedirectResponse(front + urlencode({"tab": "google", "google_error": error or "invalid_state"}))
    user_id, provider = entry
    try:
        await oauth.exchange_code(db, user_id, provider, code)
    except httpx.HTTPError:
        return RedirectResponse(front + urlencode({"tab": "google", "google_error": "token_exchange_failed"}))
    audit(db, user_id, "integration.connected", "integration", None, provider=provider)
    db.commit()
    return RedirectResponse(front + urlencode({"tab": "google", "connected": provider}))


@router.delete("/integrations/{provider}")
def disconnect(provider: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    i = db.query(Integration).filter_by(user_id=user.id, provider=provider).first()
    if i:
        db.delete(i)
        audit(db, user.id, "integration.disconnected", "integration", None, provider=provider)
        db.commit()
    return {"ok": True}


class DiscoveryIn(BaseModel):
    country: str = Field(default="", max_length=100)
    industry: str = Field(default="", max_length=100)
    company_size: str = Field(default="", max_length=50)
    job_titles: list[str] = Field(default_factory=list, max_length=20)
    business_type: str = Field(default="", max_length=100)
    keywords: str = Field(default="", max_length=300)
    min_score: int = Field(default=0, ge=0, le=100)
    limit: int = Field(default=50, ge=1, le=500)


@router.post("/discovery/search")
async def discovery(data: DiscoveryIn, user: User = Depends(get_current_user)):
    sources = [s for s in PROSPECTING_SOURCES if s.configured()]
    if not sources:
        return {"connected": False, "message": "No prospecting source connected.", "results": []}
    criteria = DiscoveryCriteria(**data.model_dump())
    results = []
    for src in sources:
        results += [r | {"source": src.key} for r in await src.search(criteria)]
    return {"connected": True, "results": results[: data.limit]}
