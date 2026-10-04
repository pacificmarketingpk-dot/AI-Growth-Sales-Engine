import json

import pytest
from pydantic import ValidationError

from app.services.ai.provider import extract_json
from app.services.ai.schemas import ConversationAnalysisResult, ProspectAnalysisResult
from app.services.scoring import lead_category, qualification_score, qualification_status
from tests.conftest import GOOD_ANALYSIS


def test_extract_json_handles_fences():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 2} hope that helps') == {"a": 2}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_score_is_recomputed_from_breakdown():
    r = ProspectAnalysisResult.model_validate({**GOOD_ANALYSIS, "lead_score": 99})
    assert r.lead_score == sum(GOOD_ANALYSIS["score_breakdown"].values()) == 85


def test_breakdown_bounds_enforced():
    bad = {**GOOD_ANALYSIS, "score_breakdown": {**GOOD_ANALYSIS["score_breakdown"], "business_fit": 30}}
    with pytest.raises(ValidationError):
        ProspectAnalysisResult.model_validate(bad)


def test_unknown_service_rejected():
    with pytest.raises(ValidationError):
        ProspectAnalysisResult.model_validate({**GOOD_ANALYSIS, "primary_service": "Everything"})


def test_generic_phrases_rejected():
    msg = "Hi John, I came across your profile and wanted to connect with you today."
    with pytest.raises(ValidationError):
        ProspectAnalysisResult.model_validate({**GOOD_ANALYSIS, "connection_message": msg})


def test_conversation_intent_normalised():
    from tests.conftest import GOOD_CONVERSATION
    assert ConversationAnalysisResult.model_validate({**GOOD_CONVERSATION, "intent": "high"}).intent == "HIGH INTENT"
    with pytest.raises(ValidationError):
        ConversationAnalysisResult.model_validate({**GOOD_CONVERSATION, "intent": "MAYBE"})


@pytest.mark.parametrize("score,cat", [(100, "HOT"), (90, "HOT"), (89, "HIGH"), (75, "HIGH"), (74, "MEDIUM"),
                                       (60, "MEDIUM"), (59, "LOW"), (0, "LOW"), (None, None)])
def test_lead_categories(score, cat):
    assert lead_category(score) == cat


def test_qualification():
    full = {"need": 25, "budget": 15, "authority": 20, "timeline": 15, "current_solution": 10, "urgency": 15}
    assert qualification_score(full) == 100
    assert qualification_score({**full, "need": 999}) == 100  # clamped
    assert qualification_status(80) == "HOT"
    assert qualification_status(60) == "QUALIFIED"
    assert qualification_status(35) == "NURTURE"
    assert qualification_status(10) == "UNQUALIFIED"


def test_analyze_endpoint_saves_and_requires_confirmation(authed, fake_ai):
    pid = authed.post("/api/prospects", json={"name": "Sam", "company": "Acme"}).json()["id"]
    r = authed.post(f"/api/prospects/{pid}/analyze?include_website=false")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["lead_score"] == 85 and d["category"] == "HIGH" and d["status"] == "ANALYZED"
    a = d["latest_analysis"]
    assert a["model"] == "gpt-4o-mini" and a["input_tokens"] == 1000 and a["estimated_cost"] > 0
    assert a["website_retrieved"] is False
    assert {o["kind"] for o in d["outreach"]} == {"connection_message", "follow_up_1", "follow_up_2"}
    # cost control: no silent re-analysis
    assert authed.post(f"/api/prospects/{pid}/analyze").status_code == 409
    r = authed.post(f"/api/prospects/{pid}/analyze?force=true&include_website=false")
    assert r.json()["analysis_count"] == 2 and r.json()["latest_analysis"]["analysis_version"] == 2


def test_malformed_ai_output_never_saved(authed, fake_ai):
    pid = authed.post("/api/prospects", json={"name": "Sam"}).json()["id"]
    fake_ai.queue = ["garbage", json.dumps({"lead_score": 5}), "{broken"]
    r = authed.post(f"/api/prospects/{pid}/analyze?include_website=false")
    assert r.status_code == 502
    assert "temporarily unavailable" in r.json()["detail"]
    d = authed.get(f"/api/prospects/{pid}").json()
    assert d["latest_analysis"] is None and d["lead_score"] is None and d["status"] == "NEW"


def test_retry_recovers(authed, fake_ai):
    pid = authed.post("/api/prospects", json={"name": "Sam"}).json()["id"]
    fake_ai.queue = ["garbage"]
    assert authed.post(f"/api/prospects/{pid}/analyze?include_website=false").status_code == 200
    assert fake_ai.calls == 2


def test_missing_key_message(app, authed):
    app.state.ai_override = None  # fall back to real provider with no key configured
    pid = authed.post("/api/prospects", json={"name": "Sam"}).json()["id"]
    r = authed.post(f"/api/prospects/{pid}/analyze?include_website=false")
    assert r.status_code == 503 and "No API key" in r.json()["detail"]


def test_bulk_analysis_continues_after_failure(authed, fake_ai):
    import time
    ids = [authed.post("/api/prospects", json={"name": n}).json()["id"] for n in ["A1", "BROKEN", "C3"]]
    fake_ai.fail_for = {'"BROKEN"'}
    job = authed.post("/api/prospects/bulk-analyze", json={"prospect_ids": ids}).json()
    for _ in range(100):
        st = authed.get(f"/api/analysis-jobs/{job['job_id']}").json()
        if st["status"] == "done":
            break
        time.sleep(0.05)
    assert st["status"] == "done" and st["completed"] == 2 and st["failed"] == 1
    assert authed.get(f"/api/prospects/{ids[2]}").json()["lead_score"] == 85


def test_edit_and_regenerate_outreach(authed):
    pid = authed.post("/api/prospects", json={"name": "Sam"}).json()["id"]
    d = authed.post(f"/api/prospects/{pid}/analyze?include_website=false").json()
    oid = d["outreach"][0]["id"]
    r = authed.put(f"/api/outreach/{oid}", json={"message": "My own edited message"})
    assert r.json()["edited"] is True and r.json()["message"] == "My own edited message"
    r = authed.post(f"/api/outreach/{oid}/regenerate")
    assert r.status_code == 200 and r.json()["edited"] is False
