from app.api.conversations import parse_transcript
from tests.conftest import GOOD_CONVERSATION


def _analyzed_prospect(c):
    pid = c.post("/api/prospects", json={"name": "Sam Lee", "company": "Acme"}).json()["id"]
    c.post(f"/api/prospects/{pid}/analyze?include_website=false")
    return pid


def test_parse_transcript():
    msgs = parse_transcript("Me: Hi Sam\nSam Lee: We're struggling with Meta leads.\nIt's been rough.", "Sam Lee")
    assert [m.sender for m in msgs] == ["me", "prospect"]
    assert "rough" in msgs[1].body


def test_high_intent_conversation_qualifies_and_appears_in_hot_leads(authed):
    pid = _analyzed_prospect(authed)
    authed.post(f"/api/prospects/{pid}/contacted", json={"channel": "LinkedIn"})
    conv = authed.post("/api/conversations", json={
        "prospect_id": pid,
        "raw_text": "Me: How's lead gen going?\nSam: We're currently struggling to generate qualified leads through Meta."
    }).json()
    r = authed.post(f"/api/conversations/{conv['id']}/analyze")
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["intent"] == "HIGH INTENT"
    assert a["analysis"]["pain_point"] == "Qualified lead generation"
    assert a["analysis"]["recommended_next_action"] == "Human takeover"
    p = authed.get(f"/api/prospects/{pid}").json()
    assert p["status"] == "QUALIFIED" and p["takeover_required"] is True
    assert p["qualification"]["score"] == 76 and p["qualification"]["status"] == "QUALIFIED"
    hot = authed.get("/api/leads/hot?sort=intent").json()
    assert hot[0]["prospect"]["id"] == pid and hot[0]["intent"] == "HIGH INTENT"
    assert authed.get("/api/leads/takeover").json()[0]["suggested_reply"]
    # take over clears the flag
    assert authed.post(f"/api/prospects/{pid}/takeover").json()["takeover_required"] is False


def test_not_interested_does_not_qualify(authed, fake_ai):
    pid = _analyzed_prospect(authed)
    fake_ai.queue = [{**GOOD_CONVERSATION, "intent": "NOT INTERESTED", "human_takeover": False,
                      "qualification": {"need": 0, "budget": 0, "authority": 10, "timeline": 0,
                                        "current_solution": 5, "urgency": 0}}]
    conv = authed.post("/api/conversations", json={"prospect_id": pid, "messages": [
        {"sender": "prospect", "body": "No thanks, we have an agency."}]}).json()
    authed.post(f"/api/conversations/{conv['id']}/analyze")
    p = authed.get(f"/api/prospects/{pid}").json()
    assert p["status"] == "REPLIED" and p["qualification"]["status"] == "UNQUALIFIED"
    assert p["takeover_required"] is False


def test_manual_qualification(authed):
    pid = authed.post("/api/prospects", json={"name": "Q"}).json()["id"]
    r = authed.put(f"/api/prospects/{pid}/qualification", json={
        "need": 25, "budget": 15, "authority": 20, "timeline": 10, "current_solution": 5, "urgency": 10})
    assert r.json()["qualification"]["score"] == 85 and r.json()["qualification"]["status"] == "HOT"
    assert r.json()["status"] == "QUALIFIED"


def test_empty_conversation_rejected(authed):
    pid = authed.post("/api/prospects", json={"name": "Q"}).json()["id"]
    assert authed.post("/api/conversations", json={"prospect_id": pid}).status_code == 422
