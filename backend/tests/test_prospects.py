from tests.conftest import register


def test_crud(authed):
    r = authed.post("/api/prospects", json={"name": "Sam Lee", "company": "Acme SaaS", "email": "sam@acme.io",
                                            "website": "acme.io"})
    assert r.status_code == 201
    p = r.json()
    assert p["status"] == "NEW" and p["website"] == "https://acme.io"
    assert authed.get(f"/api/prospects/{p['id']}").json()["name"] == "Sam Lee"
    r = authed.put(f"/api/prospects/{p['id']}", json={"job_title": "CEO", "status": "REVIEW"})
    assert r.json()["job_title"] == "CEO" and r.json()["status"] == "REVIEW"
    lst = authed.get("/api/prospects?q=acme").json()
    assert lst["total"] == 1
    assert authed.delete(f"/api/prospects/{p['id']}").status_code == 204
    assert authed.get(f"/api/prospects/{p['id']}").status_code == 404


def test_validation(authed):
    assert authed.post("/api/prospects", json={"name": ""}).status_code == 422
    assert authed.post("/api/prospects", json={"name": "A", "email": "bad"}).status_code == 422
    assert authed.post("/api/prospects", json={"name": "A", "linkedin_url": "https://evil.com/x"}).status_code == 422


def test_other_users_cannot_access(authed):
    pid = authed.post("/api/prospects", json={"name": "Private"}).json()["id"]
    authed.post("/api/auth/logout")
    register(authed, email="other@example.com")
    assert authed.get(f"/api/prospects/{pid}").status_code == 404
    assert authed.put(f"/api/prospects/{pid}", json={"notes": "x"}).status_code == 404
    assert authed.delete(f"/api/prospects/{pid}").status_code == 404
    assert authed.get("/api/prospects").json()["total"] == 0


def test_sql_injection_in_search_is_harmless(authed):
    authed.post("/api/prospects", json={"name": "Real"})
    r = authed.get("/api/prospects", params={"q": "' OR 1=1; DROP TABLE prospects; --"})
    assert r.status_code == 200 and r.json()["total"] == 0
    assert authed.get("/api/prospects").json()["total"] == 1
