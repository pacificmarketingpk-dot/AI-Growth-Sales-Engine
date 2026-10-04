from fastapi.testclient import TestClient

from tests.conftest import register


def test_register_login_me_logout(client):
    register(client)
    assert client.get("/api/auth/me").json()["email"] == "me@example.com"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    r = client.post("/api/auth/login", json={"email": "me@example.com", "password": "correct-horse-1"})
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_wrong_password_and_short_password(client):
    register(client)
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "me@example.com", "password": "nope"}).status_code == 401
    r = client.post("/api/auth/register", json={"email": "x@example.com", "password": "short"})
    assert r.status_code == 422


def test_password_is_hashed(client, db):
    from app.models import User
    register(client)
    u = db.query(User).first()
    assert u.password_hash != "correct-horse-1" and u.password_hash.startswith("$2")


def test_csrf_header_required(app):
    with TestClient(app) as c:  # no X-Requested-With header
        r = c.post("/api/auth/register", json={"email": "a@example.com", "password": "correct-horse-1"})
        assert r.status_code == 403


def test_revoke_sessions_invalidates_old_token(authed):
    old = authed.post("/api/auth/api-token").json()["token"]
    assert authed.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"}).status_code == 200
    authed.post("/api/auth/revoke-sessions")
    assert authed.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"}).status_code == 401


def test_login_rate_limited(client):
    register(client)
    codes = [client.post("/api/auth/login", json={"email": "me@example.com", "password": "bad"}).status_code
             for _ in range(12)]
    assert 429 in codes


def test_unauthenticated_blocked(client):
    assert client.get("/api/prospects").status_code == 401
    assert client.get("/api/dashboard").status_code == 401


def test_rate_limit_key_ignores_spoofed_forwarded_for(monkeypatch):
    from starlette.requests import Request
    from app.config import get_settings
    from app.utils.rate_limit import client_key

    def req(headers):
        return Request({"type": "http", "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
                        "client": ("10.0.0.9", 1234)})
    # X-Forwarded-For is client-controlled and must never become the key
    assert client_key(req({"x-forwarded-for": "1.2.3.4"})) == "10.0.0.9"
    # X-Real-IP is only trusted when explicitly behind our proxy
    assert client_key(req({"x-real-ip": "5.6.7.8"})) == "10.0.0.9"
    monkeypatch.setattr(get_settings(), "trust_proxy_headers", True)
    assert client_key(req({"x-real-ip": "5.6.7.8"})) == "5.6.7.8"


def test_weak_secret_refused_in_production(monkeypatch):
    import pytest
    from app.config import get_settings
    from app.main import create_app
    monkeypatch.setattr(get_settings(), "environment", "production")
    monkeypatch.setattr(get_settings(), "secret_key", "change-me")
    with pytest.raises(RuntimeError):
        create_app(create_tables=False)
