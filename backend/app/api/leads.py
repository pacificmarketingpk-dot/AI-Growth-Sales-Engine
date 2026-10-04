from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.common import prospect_out
from app.auth.deps import get_current_user
from app.database.session import get_db
from app.models import Conversation, Prospect, ProspectStatus, User

router = APIRouter(prefix="/api/leads", tags=["leads"])
INTENT_RANK = {"QUALIFIED": 4, "HIGH INTENT": 3, "INTERESTED": 2, "NEEDS FOLLOW-UP": 1}


def _card(p: Prospect) -> dict:
    convs = sorted([c for c in p.conversations if c.analyzed_at], key=lambda c: c.analyzed_at, reverse=True)
    latest = convs[0] if convs else None
    a = p.latest_analysis.result if p.latest_analysis else {}
    ca = (latest.analysis or {}) if latest else {}
    return {
        "prospect": prospect_out(p).model_dump(),
        "intent": latest.intent if latest else None,
        "conversation_id": latest.id if latest else None,
        "recent_response_at": latest.last_message_at.isoformat() if latest and latest.last_message_at else None,
        "pain_point": ca.get("pain_point") or a.get("business_problem"),
        "growth_opportunity": a.get("growth_opportunity"),
        "recommended_service": ca.get("recommended_service") or a.get("primary_service"),
        "summary": ca.get("summary"),
        "suggested_reply": ca.get("suggested_reply"),
        "qualification_questions": ca.get("qualification_questions", []),
        "qualification": ({"score": p.qualification.score, "status": p.qualification.status}
                          if p.qualification else None),
        "takeover_required": p.takeover_required,
    }


@router.get("/hot")
def hot_leads(sort: str = Query("score", pattern="^(score|intent|recent|opportunity)$"),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    hot_intents = list(INTENT_RANK)
    prospect_ids_with_intent = db.query(Conversation.prospect_id).filter(
        Conversation.user_id == user.id, Conversation.intent.in_(hot_intents))
    rows = db.query(Prospect).filter(Prospect.user_id == user.id, Prospect.status != ProspectStatus.LOST, or_(
        Prospect.lead_score >= 75, Prospect.status == ProspectStatus.QUALIFIED,
        Prospect.takeover_required.is_(True), Prospect.id.in_(prospect_ids_with_intent))).all()
    cards = [_card(p) for p in rows]
    keys = {
        "score": lambda c: (c["prospect"]["lead_score"] or 0),
        "intent": lambda c: (INTENT_RANK.get(c["intent"] or "", 0), c["prospect"]["lead_score"] or 0),
        "recent": lambda c: c["recent_response_at"] or "",
        "opportunity": lambda c: ((c["qualification"] or {}).get("score", 0), c["prospect"]["lead_score"] or 0),
    }
    return sorted(cards, key=keys[sort], reverse=True)


@router.get("/qualified")
def qualified_leads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Prospect).filter(Prospect.user_id == user.id, Prospect.status == ProspectStatus.QUALIFIED).all()
    return [_card(p) for p in rows]


@router.get("/takeover")
def takeover_queue(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Prospect).filter(Prospect.user_id == user.id, Prospect.takeover_required.is_(True)).all()
    return [_card(p) for p in rows]
