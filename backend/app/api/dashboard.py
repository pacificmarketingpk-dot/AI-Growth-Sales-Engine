from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database.session import get_db
from app.models import (AuditLog, Conversation, Meeting, Outreach, Prospect, ProspectAnalysis, ProspectStatus,
                        User)
from app.services.scoring import safe_rate

router = APIRouter(prefix="/api", tags=["dashboard"])
S = ProspectStatus
# Statuses that imply a prospect has reached at least that funnel stage
CONTACTED_PLUS = [S.CONTACTED, S.REPLIED, S.QUALIFIED, S.PROPOSAL, S.WON, S.LOST]
REPLIED_PLUS = [S.REPLIED, S.QUALIFIED, S.PROPOSAL, S.WON]
QUALIFIED_PLUS = [S.QUALIFIED, S.PROPOSAL, S.WON]
PROPOSAL_PLUS = [S.PROPOSAL, S.WON]


def funnel(db: Session, user_id: int, include_demo: bool, since: datetime | None = None) -> dict:
    base = db.query(Prospect).filter(Prospect.user_id == user_id)
    if not include_demo:
        base = base.filter(Prospect.is_demo.is_(False))
    if since:
        base = base.filter(Prospect.created_at >= since)
    count = lambda statuses: base.filter(Prospect.status.in_(statuses)).count()  # noqa: E731
    contacted = base.filter((Prospect.status.in_(CONTACTED_PLUS)) | (Prospect.last_contacted_at.isnot(None))).count()
    responses = count(REPLIED_PLUS)
    # Prospects who replied then lost still count as responses
    lost_after_reply = base.filter(Prospect.status == S.LOST, Prospect.conversations.any()).count()
    meeting_q = db.query(Meeting).join(Prospect).filter(Meeting.user_id == user_id)
    if not include_demo:
        meeting_q = meeting_q.filter(Prospect.is_demo.is_(False))
    if since:
        meeting_q = meeting_q.filter(Meeting.created_at >= since)
    meetings_prospects = meeting_q.with_entities(Meeting.prospect_id).distinct().count()
    return {
        "total": base.count(),
        "analyzed": base.filter(Prospect.lead_score.isnot(None)).count(),
        "contacted": contacted,
        "responses": responses + lost_after_reply,
        "qualified": count(QUALIFIED_PLUS),
        "meetings": meeting_q.count(),
        "meeting_prospects": meetings_prospects,
        "proposals": count(PROPOSAL_PLUS),
        "won": count([S.WON]),
        "base": base,
    }


@router.get("/dashboard")
def dashboard(include_demo: bool = True, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    f = funnel(db, user.id, include_demo)
    base = f.pop("base")
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    scores = [s for (s,) in base.with_entities(Prospect.lead_score).filter(Prospect.lead_score.isnot(None))]
    conf_q = db.query(func.avg(ProspectAnalysis.confidence)).join(Prospect).filter(Prospect.user_id == user.id)
    if not include_demo:
        conf_q = conf_q.filter(Prospect.is_demo.is_(False))
    avg_conf = conf_q.scalar()
    latest = (db.query(ProspectAnalysis).join(Prospect).filter(Prospect.user_id == user.id)
              .order_by(ProspectAnalysis.analyzed_at.desc()).limit(300).all())
    opp = Counter(a.result.get("primary_service") for a in latest if include_demo or not a.prospect.is_demo)
    mq = db.query(Meeting).join(Prospect).filter(Meeting.user_id == user.id, Meeting.status == "scheduled")
    if not include_demo:
        mq = mq.filter(Prospect.is_demo.is_(False))
    upcoming = mq.filter(Meeting.start_at >= now).order_by(Meeting.start_at).limit(5).all()
    has_demo = db.query(Prospect.id).filter(Prospect.user_id == user.id, Prospect.is_demo.is_(True)).first() is not None
    recent = (db.query(AuditLog).filter(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc())
              .limit(8).all())
    return {
        "has_demo_data": has_demo,
        "prospects": {"total": f["total"], "new": base.filter(Prospect.status == S.NEW).count(),
                      "analyzed": f["analyzed"],
                      "high_priority": base.filter(Prospect.lead_score >= 75).count()},
        "sales": {"contacted": f["contacted"], "responses": f["responses"], "qualified": f["qualified"],
                  "meetings": f["meetings"], "proposals": f["proposals"], "won": f["won"]},
        "ai": {"average_score": round(sum(scores) / len(scores), 1) if scores else None,
               "hot_count": len([s for s in scores if s >= 90]),
               "average_confidence": round(avg_conf, 2) if avg_conf is not None else None,
               "top_opportunity": opp.most_common(1)[0][0] if opp else None},
        "meetings": {"upcoming": mq.filter(Meeting.start_at >= now).count(),
                     "this_week": mq.filter(Meeting.start_at >= week_start,
                                            Meeting.start_at < week_start + timedelta(days=7)).count(),
                     "booked": f["meetings"],
                     "next": [{"id": m.id, "title": m.title, "start_at": m.start_at.isoformat(),
                               "prospect_id": m.prospect_id, "prospect_name": m.prospect.name} for m in upcoming]},
        "recent_activity": [{"action": r.action, "entity_type": r.entity_type, "entity_id": r.entity_id,
                             "created_at": r.created_at.isoformat(), "details": r.details} for r in recent],
    }


@router.get("/analytics")
def analytics(days: int = Query(90, ge=7, le=730), include_demo: bool = False,
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    f = funnel(db, user.id, include_demo, since)
    base = f.pop("base")
    scores = [s for (s,) in base.with_entities(Prospect.lead_score).filter(Prospect.lead_score.isnot(None))]
    rates = {
        "contact_rate": safe_rate(f["contacted"], f["total"]),
        "response_rate": safe_rate(f["responses"], f["contacted"]),
        "qualification_rate": safe_rate(f["qualified"], f["responses"]),
        "meeting_rate": safe_rate(f["meeting_prospects"], f["qualified"]),
        "proposal_rate": safe_rate(f["proposals"], f["meeting_prospects"]),
        "win_rate": safe_rate(f["won"], f["proposals"]),
    }
    # weekly series
    weeks = []
    rows = base.with_entities(Prospect.created_at, Prospect.lead_score).all()
    for i in range(min(days // 7, 26), -1, -1):
        start = (now - timedelta(weeks=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        start -= timedelta(days=start.weekday())
        end = start + timedelta(days=7)
        inwk = [r for r in rows if r[0] and start <= _aware(r[0]) < end]
        weeks.append({"week": start.date().isoformat(), "added": len(inwk),
                      "analyzed": len([r for r in inwk if r[1] is not None])})
    buckets = {"HOT": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for s in scores:
        buckets["HOT" if s >= 90 else "HIGH" if s >= 75 else "MEDIUM" if s >= 60 else "LOW"] += 1
    intents = Counter(i for (i,) in db.query(Conversation.intent).filter(
        Conversation.user_id == user.id, Conversation.intent.isnot(None), Conversation.created_at >= since))
    channels = Counter(c for (c,) in db.query(Outreach.channel).join(Prospect).filter(
        Prospect.user_id == user.id, Outreach.contacted_at.isnot(None), Outreach.contacted_at >= since))
    return {
        "days": days,
        "counts": {"prospects_added": f["total"], "prospects_analyzed": f["analyzed"], "contacted": f["contacted"],
                   "responses": f["responses"], "qualified": f["qualified"], "meetings": f["meetings"],
                   "proposals": f["proposals"], "won": f["won"]},
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "rates": rates,
        "funnel": [{"stage": k, "value": f[v]} for k, v in [
            ("Prospects", "total"), ("Analyzed", "analyzed"), ("Contacted", "contacted"),
            ("Responded", "responses"), ("Qualified", "qualified"), ("Meeting", "meeting_prospects"),
            ("Proposal", "proposals"), ("Won", "won")]],
        "weekly": weeks,
        "score_distribution": [{"category": k, "count": v} for k, v in buckets.items()],
        "intents": [{"intent": k, "count": v} for k, v in intents.most_common()],
        "channels": [{"channel": k, "count": v} for k, v in channels.most_common()],
    }


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
