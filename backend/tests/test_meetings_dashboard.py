from datetime import datetime, timedelta, timezone

from app.models import Integration
from app.services.google import calendar as cal
from app.utils.crypto import decrypt_json, encrypt_json


def future(days=2):
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


def test_meeting_requires_calendar_when_sync_requested(authed):
    pid = authed.post("/api/prospects", json={"name": "Sam"}).json()["id"]
    r = authed.post("/api/meetings", json={"prospect_id": pid, "start_at": future()})
    assert r.status_code == 409 and "not connected" in r.json()["detail"]


def test_meeting_without_sync_uses_defaults(authed):
    pid = authed.post("/api/prospects", json={"name": "Sam", "company": "Acme"}).json()["id"]
    r = authed.post("/api/meetings", json={"prospect_id": pid, "start_at": future(), "sync_to_google": False})
    assert r.status_code == 201
    m = r.json()
    assert m["duration_minutes"] == 30 and m["meeting_type"] == "Digital Growth Consultation"
    assert m["calendar_synced"] is False and m["title"].startswith("Digital Growth Consultation: Sam")
    assert authed.get("/api/meetings?scope=upcoming").json()[0]["id"] == m["id"]


def test_meeting_in_past_rejected(authed):
    pid = authed.post("/api/prospects", json={"name": "Sam"}).json()["id"]
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert authed.post("/api/meetings", json={"prospect_id": pid, "start_at": past,
                                              "sync_to_google": False}).status_code == 422


def test_meeting_synced_with_google(authed, db, monkeypatch):
    uid = authed.get("/api/auth/me").json()["id"]
    db.add(Integration(user_id=uid, provider="google_calendar", status="CONNECTED",
                       encrypted_tokens=encrypt_json({"access_token": "t", "expires_at": 9e12}), config={}))
    db.commit()
    captured = {}

    async def fake_create(db, user_id, **kw):
        captured.update(kw)
        return {"id": "evt1", "htmlLink": "https://calendar.google.com/event?eid=1"}
    monkeypatch.setattr(cal, "create_event", fake_create)
    pid = authed.post("/api/prospects", json={"name": "Sam", "email": "s@a.io"}).json()["id"]
    r = authed.post("/api/meetings", json={"prospect_id": pid, "start_at": future(), "invite_prospect": True})
    assert r.status_code == 201, r.text
    assert r.json()["calendar_synced"] is True and captured["attendee_email"] == "s@a.io"


def test_token_encryption_roundtrip():
    blob = encrypt_json({"access_token": "secret"})
    assert "secret" not in blob and decrypt_json(blob)["access_token"] == "secret"


def test_free_slots_excludes_busy():
    now = datetime.now(timezone.utc)
    slots = cal.free_slots([], days=7)
    assert slots and all(datetime.fromisoformat(s) > now for s in slots)
    busy_start = datetime.fromisoformat(slots[0])
    blocked = cal.free_slots([{"start": busy_start.isoformat(),
                               "end": (busy_start + timedelta(minutes=30)).isoformat()}], days=7)
    assert slots[0] not in blocked


def test_dashboard_calculations(authed):
    empty = authed.get("/api/dashboard").json()
    assert empty["prospects"]["total"] == 0 and empty["ai"]["average_score"] is None
    ids = [authed.post("/api/prospects", json={"name": f"P{i}"}).json()["id"] for i in range(4)]
    authed.post(f"/api/prospects/{ids[0]}/analyze?include_website=false")
    authed.post(f"/api/prospects/{ids[1]}/analyze?include_website=false")
    authed.post(f"/api/prospects/{ids[0]}/contacted", json={"channel": "LinkedIn"})
    authed.put(f"/api/prospects/{ids[1]}", json={"status": "PROPOSAL"})
    authed.put(f"/api/prospects/{ids[2]}", json={"status": "WON"})
    d = authed.get("/api/dashboard").json()
    assert d["prospects"] == {"total": 4, "new": 1, "analyzed": 2, "high_priority": 2}
    assert d["sales"]["contacted"] == 3 and d["sales"]["proposals"] == 2 and d["sales"]["won"] == 1
    assert d["ai"]["average_score"] == 85.0 and d["ai"]["top_opportunity"] == "Landing Pages"
    a = authed.get("/api/analytics?days=30").json()
    assert a["rates"]["win_rate"] == 50.0
    assert a["rates"]["response_rate"] == round(2 / 3 * 100, 1)


def test_demo_data_is_labelled_and_separable(authed):
    authed.post("/api/demo/seed")
    items = authed.get("/api/prospects").json()["items"]
    assert items and all(p["is_demo"] and "DEMO" in p["name"] for p in items)
    assert authed.get("/api/dashboard?include_demo=false").json()["prospects"]["total"] == 0
    assert authed.get("/api/dashboard").json()["prospects"]["total"] == 5
    authed.delete("/api/demo")
    assert authed.get("/api/prospects").json()["total"] == 0


def test_integrations_report_honest_status(authed):
    d = authed.get("/api/integrations").json()
    by = {i["provider"]: i for i in d["integrations"]}
    assert by["google_calendar"]["status"] == "NOT_CONNECTED" and by["google_calendar"]["available"] is False
    assert by["linkedin"]["status"] == "NOT_CONNECTED"
    assert authed.post("/api/integrations/google_calendar/connect").status_code == 409
    assert authed.post("/api/integrations/linkedin/connect").status_code == 409
    disc = authed.post("/api/discovery/search", json={"country": "USA"}).json()
    assert disc == {"connected": False, "message": "No prospecting source connected.", "results": []}


def test_audit_log_records_actions(authed):
    pid = authed.post("/api/prospects", json={"name": "Sam"}).json()["id"]
    authed.post(f"/api/prospects/{pid}/analyze?include_website=false")
    actions = {r["action"] for r in authed.get("/api/audit").json()}
    assert {"prospect.created", "prospect.analyzed", "message.generated"} <= actions
