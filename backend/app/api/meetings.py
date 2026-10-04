import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, get_owned_prospect
from app.database.session import get_db
from app.models import Integration, Meeting, User, UserSettings
from app.schemas.api import MeetingCreate, MeetingOut, MeetingUpdate
from app.services.audit import audit
from app.services.google import calendar
from app.services.google.oauth import GoogleNotConnected

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["meetings"])


def meeting_out(m: Meeting) -> MeetingOut:
    p = m.prospect
    a = p.latest_analysis.result if p.latest_analysis else {}
    conv = next((c for c in sorted(p.conversations, key=lambda c: c.id, reverse=True) if c.analysis), None)
    fields = {f: getattr(m, f) for f in MeetingOut.model_fields if f != "prospect"}
    return MeetingOut(**fields, prospect={
        "id": p.id, "name": p.name, "company": p.company, "email": p.email, "lead_score": p.lead_score,
        "is_demo": p.is_demo,
        "business_problem": (conv.analysis.get("pain_point") if conv else None) or a.get("business_problem"),
        "growth_opportunity": a.get("growth_opportunity"),
        "recommended_service": (conv.analysis.get("recommended_service") if conv else None) or a.get("primary_service"),
        "qualification_notes": (f"{p.qualification.status} ({p.qualification.score}/100)"
                                + (f" - {p.qualification.notes}" if p.qualification.notes else ""))
        if p.qualification else None,
    })


def _calendar_connected(db: Session, user_id: int) -> bool:
    return db.query(Integration).filter_by(user_id=user_id, provider="google_calendar",
                                           status="CONNECTED").first() is not None


@router.get("/meetings", response_model=list[MeetingOut])
def list_meetings(scope: str = "all", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Meeting).filter(Meeting.user_id == user.id)
    now = datetime.now(timezone.utc)
    if scope == "upcoming":
        q = q.filter(Meeting.start_at >= now, Meeting.status == "scheduled")
    elif scope == "past":
        q = q.filter(Meeting.start_at < now)
    return [meeting_out(m) for m in q.order_by(Meeting.start_at.asc()).limit(500)]


@router.post("/meetings", response_model=MeetingOut, status_code=201)
async def create_meeting(data: MeetingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = get_owned_prospect(data.prospect_id, db, user)
    us = db.query(UserSettings).filter_by(user_id=user.id).first() or UserSettings(user_id=user.id)
    start = data.start_at if data.start_at.tzinfo else data.start_at.replace(tzinfo=timezone.utc)
    if start < datetime.now(timezone.utc) - timedelta(minutes=5):
        raise HTTPException(422, "Choose a time in the future.")
    mtype = data.meeting_type or us.meeting_title
    minutes = data.duration_minutes or us.meeting_duration
    title = data.title or f"{mtype}: {p.name}" + (f" ({p.company})" if p.company else "")
    m = Meeting(user_id=user.id, prospect_id=p.id, title=title, meeting_type=mtype, start_at=start,
                duration_minutes=minutes, notes=data.notes)

    if data.sync_to_google:
        if not _calendar_connected(db, user.id):
            raise HTTPException(409, "Google Calendar is not connected. Connect it in Settings, "
                                     "or save the meeting without calendar sync.")
        desc = "\n".join(filter(None, [
            f"Prospect: {p.name}" + (f", {p.job_title}" if p.job_title else ""),
            f"Company: {p.company}" if p.company else None,
            f"Notes: {data.notes}" if data.notes else None]))
        try:
            ev = await calendar.create_event(db, user.id, title=title, start=start, minutes=minutes, description=desc,
                                             attendee_email=p.email if data.invite_prospect else None, tz=us.timezone)
            m.google_event_id, m.google_event_link, m.calendar_synced = ev.get("id"), ev.get("htmlLink"), True
        except GoogleNotConnected:
            raise HTTPException(409, "Google Calendar connection expired. Reconnect it in Settings.")
        except httpx.HTTPError:
            log.exception("calendar create failed")
            raise HTTPException(502, "Google Calendar did not accept the event. Please try again.")
    db.add(m)
    db.flush()
    audit(db, user.id, "meeting.booked", "meeting", m.id, prospect_id=p.id, synced=m.calendar_synced)
    db.commit()
    db.refresh(m)
    return meeting_out(m)


@router.put("/meetings/{mid}", response_model=MeetingOut)
def update_meeting(mid: int, data: MeetingUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    m = db.get(Meeting, mid)
    if not m or m.user_id != user.id:
        raise HTTPException(404, "Meeting not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return meeting_out(m)


@router.get("/calendar/events")
async def calendar_events(days: int = 14, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _calendar_connected(db, user.id):
        return {"connected": False, "message": "Google Calendar is not connected.", "events": [], "free_slots": []}
    try:
        events = await calendar.list_events(db, user.id, days=min(max(days, 1), 60))
    except GoogleNotConnected:
        return {"connected": False, "message": "Google Calendar connection expired. Reconnect it in Settings.",
                "events": [], "free_slots": []}
    except httpx.HTTPError:
        raise HTTPException(502, "Google Calendar is unavailable right now.")
    us = db.query(UserSettings).filter_by(user_id=user.id).first()
    return {"connected": True, "events": events,
            "free_slots": calendar.free_slots(events, minutes=us.meeting_duration if us else 30)}
