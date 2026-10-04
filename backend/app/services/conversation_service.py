from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Conversation, LeadQualification, ProspectStatus, UserSettings
from app.services.ai import prompts
from app.services.ai.factory import provider_for_user
from app.services.ai.schemas import ConversationAnalysisResult
from app.services.audit import audit
from app.services.notifications import notify_qualified_lead
from app.services.scoring import qualification_score, qualification_status

ADVANCED = {ProspectStatus.PROPOSAL, ProspectStatus.WON, ProspectStatus.LOST}


def transcript(conv: Conversation) -> str:
    return "\n".join(f"[{m.sender}] {m.body}" for m in conv.messages)


async def analyze_conversation(db: Session, conv: Conversation, provider=None) -> Conversation:
    if not conv.messages:
        raise ValueError("Add at least one message before analyzing.")
    us = db.query(UserSettings).filter_by(user_id=conv.user_id).first() or UserSettings(user_id=conv.user_id)
    p = conv.prospect
    provider = provider or provider_for_user(us, p.is_demo)
    context = {"prospect": {"name": p.name, "company": p.company, "job_title": p.job_title, "industry": p.industry},
               "latest_analysis": (p.latest_analysis.result.get("growth_opportunity") if p.latest_analysis else None)}
    result = await provider.generate(prompts.conversation_system(us.message_tone),
                                     f"CONTEXT: {context}\nCONVERSATION:\n{transcript(conv)}",
                                     ConversationAnalysisResult)
    out: ConversationAnalysisResult = result.data
    conv.intent = out.intent
    conv.analysis = out.model_dump() | {"model": result.model, "estimated_cost": result.estimated_cost}
    conv.analyzed_at = datetime.now(timezone.utc)

    signals = out.qualification.model_dump()
    score = qualification_score(signals)
    q = p.qualification or LeadQualification(prospect_id=p.id)
    for k, v in signals.items():
        setattr(q, k, v)
    q.score, q.status = score, qualification_status(score)
    if not p.qualification:
        db.add(q)

    if any(m.sender == "prospect" for m in conv.messages) and p.status in (
            ProspectStatus.NEW, ProspectStatus.ANALYZED, ProspectStatus.REVIEW, ProspectStatus.APPROVED,
            ProspectStatus.CONTACTED):
        p.status = ProspectStatus.REPLIED
    became_qualified = False
    if out.intent in ("HIGH INTENT", "QUALIFIED") and score >= 60 and p.status not in ADVANCED:
        became_qualified = p.status != ProspectStatus.QUALIFIED
        p.status = ProspectStatus.QUALIFIED
    p.takeover_required = bool(out.human_takeover or out.intent in ("HIGH INTENT", "QUALIFIED")) and not p.taken_over_at

    audit(db, conv.user_id, "conversation.analyzed", "conversation", conv.id, intent=out.intent, qualification=score)
    if became_qualified:
        audit(db, conv.user_id, "lead.qualified", "prospect", p.id, score=score)
    db.commit()
    if became_qualified and us.email_notifications:
        notify_qualified_lead(us, p, out)
    return conv
