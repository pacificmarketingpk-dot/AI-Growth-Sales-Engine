"""Final acceptance workflow from the spec (Google Calendar is mocked at the HTTP boundary)."""
from datetime import datetime, timedelta, timezone

from app.models import Integration
from app.services.google import calendar as cal
from app.utils.crypto import encrypt_json


def test_full_workflow(client, db, monkeypatch):
    # 1. log in
    client.post("/api/auth/register", json={"email": "c@x.io", "password": "correct-horse-1"})
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "c@x.io", "password": "correct-horse-1"}).status_code == 200
    # 2-4. add + save prospect
    pid = client.post("/api/prospects", json={"name": "John Smith", "company": "ABC SaaS", "job_title": "CEO",
                                              "industry": "SaaS", "email": "john@abc.io"}).json()["id"]
    # 5-11. analyze
    p = client.post(f"/api/prospects/{pid}/analyze?include_website=false").json()
    a = p["latest_analysis"]["result"]
    assert p["lead_score"] and a["business_problem"] and a["growth_opportunity"] and a["primary_service"]
    msg = next(o for o in p["outreach"] if o["kind"] == "connection_message")
    # 12. edit (13. copy is client-side)
    assert client.put(f"/api/outreach/{msg['id']}", json={"message": "Edited by me, John."}).json()["edited"]
    # 14. contacted
    assert client.post(f"/api/prospects/{pid}/contacted", json={"outreach_id": msg["id"]}).json()["status"] == "CONTACTED"
    # 15-18. conversation
    conv = client.post("/api/conversations", json={"prospect_id": pid, "raw_text":
                       "John: We're currently struggling to generate qualified leads through Meta."}).json()
    assert client.post(f"/api/conversations/{conv['id']}/analyze").json()["intent"] == "HIGH INTENT"
    assert client.get(f"/api/prospects/{pid}").json()["status"] == "QUALIFIED"
    # 19. hot leads
    assert any(c["prospect"]["id"] == pid for c in client.get("/api/leads/hot").json())
    # 20-23. book via Google Calendar
    uid = client.get("/api/auth/me").json()["id"]
    db.add(Integration(user_id=uid, provider="google_calendar", status="CONNECTED",
                       encrypted_tokens=encrypt_json({"access_token": "t", "expires_at": 9e12}), config={}))
    db.commit()

    async def fake_create(db, user_id, **kw):
        return {"id": "evt", "htmlLink": "https://calendar.google.com/x"}
    monkeypatch.setattr(cal, "create_event", fake_create)
    start = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    m = client.post("/api/meetings", json={"prospect_id": pid, "start_at": start}).json()
    assert m["calendar_synced"] and m["prospect"]["recommended_service"]
    assert client.get("/api/meetings").json()[0]["id"] == m["id"]
    # 24. dashboard updates
    d = client.get("/api/dashboard").json()
    assert d["sales"]["qualified"] == 1 and d["meetings"]["booked"] == 1 and d["meetings"]["upcoming"] == 1
