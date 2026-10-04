from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.services.google.oauth import access_token

API = "https://www.googleapis.com/calendar/v3"


async def create_event(db: Session, user_id: int, *, title: str, start: datetime, minutes: int,
                       description: str, attendee_email: str | None, tz: str) -> dict:
    token = await access_token(db, user_id, "google_calendar")
    end = start + timedelta(minutes=minutes)
    body = {"summary": title, "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": tz},
            "end": {"dateTime": end.isoformat(), "timeZone": tz}}
    if attendee_email:
        body["attendees"] = [{"email": attendee_email}]
    async with httpx.AsyncClient(timeout=20) as c:
        # sendUpdates=none: the consultant decides whether Google emails the invite.
        r = await c.post(f"{API}/calendars/primary/events", params={"sendUpdates": "none"}, json=body,
                         headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()


async def list_events(db: Session, user_id: int, days: int = 14) -> list[dict]:
    token = await access_token(db, user_id, "google_calendar")
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{API}/calendars/primary/events", headers={"Authorization": f"Bearer {token}"},
                        params={"timeMin": now.isoformat(), "timeMax": (now + timedelta(days=days)).isoformat(),
                                "singleEvents": "true", "orderBy": "startTime", "maxResults": 100})
    r.raise_for_status()
    return [{"id": e["id"], "summary": e.get("summary", "(busy)"),
             "start": e["start"].get("dateTime") or e["start"].get("date"),
             "end": e["end"].get("dateTime") or e["end"].get("date"), "link": e.get("htmlLink")}
            for e in r.json().get("items", [])]


def free_slots(busy: list[dict], days: int = 7, minutes: int = 30, start_hour: int = 9, end_hour: int = 17) -> list[str]:
    """Simple availability: weekday working hours minus busy events (UTC)."""
    spans = []
    for b in busy:
        try:
            spans.append((datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"])))
        except (ValueError, TypeError):
            continue
    slots, now = [], datetime.now(timezone.utc)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for d in range(days + 1):
        cur = day + timedelta(days=d)
        if cur.weekday() >= 5:
            continue
        t = cur.replace(hour=start_hour)
        while t + timedelta(minutes=minutes) <= cur.replace(hour=end_hour):
            e = t + timedelta(minutes=minutes)
            if t > now and not any(s < e and t < f for s, f in spans if s.tzinfo):
                slots.append(t.isoformat())
            t = e
    return slots[:40]
