from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database.session import get_db
from app.models import (AuditLog, Conversation, ConversationMessage, Meeting, Prospect, ProspectStatus, User,
                        UserSettings)
from app.schemas.api import SettingsIn
from app.models import Outreach, ProspectAnalysis
from app.services.ai.demo_provider import DEMO_ANALYSIS
from app.services.ai.schemas import SCORE_WEIGHTS, ProspectAnalysisResult
from app.services.scoring import lead_category
from app.services.audit import audit

router = APIRouter(prefix="/api", tags=["settings"])
FIELDS = ["brand_name", "business", "role", "timezone", "ai_provider", "ai_model", "message_tone",
          "followup_1_days", "followup_2_days", "meeting_title", "meeting_duration", "email_notifications",
          "notification_email"]


def _get(db: Session, user: User) -> UserSettings:
    s = db.query(UserSettings).filter_by(user_id=user.id).first()
    if not s:
        s = UserSettings(user_id=user.id, notification_email=user.email)
        db.add(s)
        db.commit()
    return s


def _out(s: UserSettings, user: User) -> dict:
    return {"name": user.name, "email": user.email, **{f: getattr(s, f) for f in FIELDS}}


@router.get("/settings")
def get_settings_(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(_get(db, user), user)


@router.put("/settings")
def update_settings(data: SettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _get(db, user)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes:
        user.name = changes.pop("name") or ""
    for k, v in changes.items():
        setattr(s, k, v if v is not None else getattr(s, k))
    audit(db, user.id, "settings.updated", "settings", s.id, fields=list(changes))
    db.commit()
    return _out(s, user)


@router.get("/audit")
def audit_log(limit: int = Query(100, ge=1, le=500), user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    rows = (db.query(AuditLog).filter(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc())
            .limit(limit).all())
    return [{"id": r.id, "action": r.action, "entity_type": r.entity_type, "entity_id": r.entity_id,
             "details": r.details, "created_at": r.created_at.isoformat()} for r in rows]


# ---------- demo mode ----------
DEMO = [
    ("DEMO PROSPECT Ava", "DEMO COMPANY Northwind SaaS", "Founder & CEO", "SaaS", "USA", "11-50", 88, "QUALIFIED"),
    ("DEMO PROSPECT Ben", "DEMO COMPANY Brightlane Dental", "Marketing Director", "Healthcare", "UK", "51-200", 76,
     "CONTACTED"),
    ("DEMO PROSPECT Chloe", "DEMO COMPANY Harbor Logistics", "Growth Manager", "Logistics", "Canada", "201-500",
     64, "ANALYZED"),
    ("DEMO PROSPECT Dev", "DEMO COMPANY Pinecrest Realty", "CMO", "Real Estate", "USA", "11-50", None, "NEW"),
    ("DEMO PROSPECT Ella", "DEMO COMPANY Lumen Fitness", "Owner", "Fitness", "Australia", "1-10", 92, "REPLIED"),
]


@router.post("/demo/seed")
def seed_demo(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.query(Prospect.id).filter(Prospect.user_id == user.id, Prospect.is_demo.is_(True)).first():
        return {"ok": True, "created": 0}
    now = datetime.now(timezone.utc)
    for i, (name, company, title, industry, country, size, score, status) in enumerate(DEMO):
        p = Prospect(user_id=user.id, name=name, company=company, job_title=title, industry=industry,
                     country=country, company_size=size, status=ProspectStatus(status), source="demo",
                     is_demo=True, lead_score=score, notes="Demo record. Fake data for exploring the app.",
                     created_at=now - timedelta(days=20 - i * 3))
        db.add(p)
        db.flush()
        if score is not None:
            _demo_analysis(db, p, score)
        if status in ("QUALIFIED", "REPLIED"):
            c = Conversation(user_id=user.id, prospect_id=p.id, channel="LinkedIn", last_message_at=now)
            c.messages = [
                ConversationMessage(sender="me", body="[DEMO] Thanks for connecting - curious how lead gen is going?"),
                ConversationMessage(sender="prospect",
                                    body="[DEMO] We're currently struggling to generate qualified leads through Meta."),
            ]
            db.add(c)
        if status == "QUALIFIED":
            db.add(Meeting(user_id=user.id, prospect_id=p.id, title=f"Digital Growth Consultation: {name}",
                           start_at=now + timedelta(days=2, hours=3), duration_minutes=30,
                           notes="[DEMO] Not synced to any calendar."))
    audit(db, user.id, "demo.seeded", "prospect", None, count=len(DEMO))
    db.commit()
    return {"ok": True, "created": len(DEMO)}


@router.delete("/demo")
def clear_demo(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Prospect).filter(Prospect.user_id == user.id, Prospect.is_demo.is_(True)).all()
    for p in rows:
        db.delete(p)
    audit(db, user.id, "demo.cleared", "prospect", None, count=len(rows))
    db.commit()
    return {"ok": True, "deleted": len(rows)}


def _demo_analysis(db: Session, p: Prospect, score: int) -> None:
    """Build a clearly-labelled demo analysis whose breakdown sums to the given score."""
    keys = list(SCORE_WEIGHTS)
    breakdown = {k: min(SCORE_WEIGHTS[k], round(SCORE_WEIGHTS[k] * score / 100)) for k in keys}
    diff = score - sum(breakdown.values())
    for k in keys:
        if diff == 0:
            break
        step = 1 if diff > 0 else -1
        if 0 <= breakdown[k] + step <= SCORE_WEIGHTS[k]:
            breakdown[k] += step
            diff -= step
    data = ProspectAnalysisResult.model_validate({**DEMO_ANALYSIS, "score_breakdown": breakdown})
    db.add(ProspectAnalysis(prospect_id=p.id, analysis_version=1, lead_score=data.lead_score,
                            category=lead_category(data.lead_score), score_breakdown=breakdown,
                            result=data.model_dump(), confidence=data.confidence, provider="demo", model="demo"))
    p.lead_score = data.lead_score
    for kind in ("connection_message", "follow_up_1", "follow_up_2"):
        db.add(Outreach(prospect_id=p.id, kind=kind, message=getattr(data, kind)))
