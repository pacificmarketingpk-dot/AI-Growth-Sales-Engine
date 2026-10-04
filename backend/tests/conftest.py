import json
import os
import tempfile

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.update(DATABASE_URL=os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_db.name}", ENVIRONMENT="test", SECRET_KEY="test-secret-key-" + "x" * 32,
                  ANTHROPIC_API_KEY="", OPENAI_API_KEY="", GOOGLE_CLIENT_ID="", GOOGLE_CLIENT_SECRET="")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.ai.demo_provider import DEMO_ANALYSIS, DEMO_CONVERSATION  # noqa: E402
from app.services.ai.provider import AIProvider, AIRawResponse  # noqa: E402
from app.utils import rate_limit  # noqa: E402

GOOD_ANALYSIS = {**DEMO_ANALYSIS,
                 "business_problem": "Potential difficulty converting paid traffic.",
                 "connection_message": "Hi Sam - I help SaaS teams turn paid clicks into demos. Open to connecting?",
                 "follow_up_1": "Thanks for connecting, Sam. Do your campaigns send traffic to dedicated landing pages?",
                 "follow_up_2": "Last note - happy to share a short landing page teardown if it's useful."}
GOOD_CONVERSATION = {**DEMO_CONVERSATION, "suggested_reply": "Makes sense - want to look at the funnel together next week?"}


class FakeProvider(AIProvider):
    name = "fake"

    def __init__(self):
        super().__init__(api_key="k", model="gpt-4o-mini")
        self.queue: list = []
        self.calls = 0
        self.fail_for: set[str] = set()

    async def complete(self, system, user, max_tokens=2000):
        self.calls += 1
        for marker in self.fail_for:
            if marker in user:
                return AIRawResponse("not json at all", 10, 5)
        if self.queue:
            item = self.queue.pop(0)
            return AIRawResponse(item if isinstance(item, str) else json.dumps(item), 100, 50)
        if '"intent"' in system:
            return AIRawResponse(json.dumps(GOOD_CONVERSATION), 100, 50)
        if "lead_score" not in system:
            return AIRawResponse(json.dumps({"message": "A fresh, specific follow-up message for the prospect."}), 50, 20)
        return AIRawResponse(json.dumps(GOOD_ANALYSIS), 1000, 500)


@pytest.fixture()
def fake_ai():
    return FakeProvider()


@pytest.fixture()
def app(fake_ai):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    rate_limit.auth_limiter.hits.clear()
    rate_limit.ai_limiter.hits.clear()
    a = create_app(create_tables=False)
    a.state.ai_override = fake_ai
    a.state.session_factory = SessionLocal
    return a


@pytest.fixture()
def client(app):
    with TestClient(app, headers={"X-Requested-With": "age"}) as c:
        yield c


def register(client, email="me@example.com", password="correct-horse-1"):
    r = client.post("/api/auth/register", json={"email": email, "password": password, "name": "Me"})
    assert r.status_code == 200, r.text
    return r


@pytest.fixture()
def authed(client):
    register(client)
    return client


@pytest.fixture()
def db():
    s = SessionLocal()
    yield s
    s.close()
