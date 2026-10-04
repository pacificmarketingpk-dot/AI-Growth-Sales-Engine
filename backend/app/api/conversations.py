import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.common import ai_http_error
from app.auth.deps import get_current_user, get_owned_prospect
from app.database.session import get_db
from app.models import Conversation, ConversationMessage, User
from app.schemas.api import ConversationCreate, ConversationOut, MessageIn
from app.services.audit import audit
from app.services.conversation_service import analyze_conversation
from app.utils.rate_limit import ai_limiter

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
LINE = re.compile(r"^\s*(me|you|i|prospect|them|they|[^:]{1,60}):\s*(.+)$", re.IGNORECASE)


def parse_transcript(text: str, prospect_name: str) -> list[MessageIn]:
    """Parse 'Name: message' lines. Lines without a speaker continue the previous message."""
    msgs: list[MessageIn] = []
    first = (prospect_name or "").split(" ")[0].lower()
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = LINE.match(raw)
        if m:
            who = m.group(1).strip().lower()
            sender = "me" if who in ("me", "you", "i") else "prospect" if (
                who in ("prospect", "them", "they") or (first and first in who)) else "me"
            msgs.append(MessageIn(sender=sender, body=m.group(2).strip()))
        elif msgs:
            msgs[-1].body += "\n" + raw.strip()
        else:
            msgs.append(MessageIn(sender="prospect", body=raw.strip()))
    return msgs


def conv_out(c: Conversation) -> ConversationOut:
    o = ConversationOut.model_validate(c)
    o.prospect_name, o.prospect_company = c.prospect.name, c.prospect.company
    return o


def _owned(cid: int, db: Session, user: User) -> Conversation:
    c = db.get(Conversation, cid)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    return c


@router.get("", response_model=list[ConversationOut])
def list_conversations(prospect_id: int | None = None, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    q = db.query(Conversation).filter(Conversation.user_id == user.id)
    if prospect_id:
        q = q.filter(Conversation.prospect_id == prospect_id)
    return [conv_out(c) for c in q.order_by(Conversation.updated_at.desc()).limit(300)]


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(data: ConversationCreate, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    p = get_owned_prospect(data.prospect_id, db, user)
    msgs = list(data.messages)
    if data.raw_text:
        msgs += parse_transcript(data.raw_text, p.name)
    if not msgs:
        raise HTTPException(422, "Paste the conversation or add at least one message.")
    c = Conversation(user_id=user.id, prospect_id=p.id, channel=data.channel,
                     last_message_at=datetime.now(timezone.utc))
    c.messages = [ConversationMessage(sender=m.sender, body=m.body,
                                      sent_at=m.sent_at or datetime.now(timezone.utc)) for m in msgs]
    db.add(c)
    db.flush()
    audit(db, user.id, "conversation.created", "conversation", c.id, prospect_id=p.id, messages=len(msgs))
    db.commit()
    return conv_out(c)


@router.get("/{cid}", response_model=ConversationOut)
def get_conversation(cid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return conv_out(_owned(cid, db, user))


@router.post("/{cid}/messages", response_model=ConversationOut)
def add_message(cid: int, data: MessageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _owned(cid, db, user)
    c.messages.append(ConversationMessage(sender=data.sender, body=data.body,
                                          sent_at=data.sent_at or datetime.now(timezone.utc)))
    c.last_message_at = datetime.now(timezone.utc)
    db.commit()
    return conv_out(c)


@router.post("/{cid}/analyze", response_model=ConversationOut)
async def analyze(cid: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ai_limiter.check(f"ai:{user.id}")
    c = _owned(cid, db, user)
    try:
        await analyze_conversation(db, c, provider=getattr(request.app.state, "ai_override", None))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise ai_http_error(e)
    db.refresh(c)
    return conv_out(c)


@router.delete("/{cid}", status_code=204)
def delete_conversation(cid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _owned(cid, db, user)
    db.delete(c)
    db.commit()
