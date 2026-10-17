import json

import pytest
from fastapi.testclient import TestClient

from backend.app.challenges import REGISTRY
from backend.app.config import Settings
from backend.app.database import Base
from backend.app.main import create_app
from backend.app.transport import WorkerRejected, WorkerUnavailable
from worker.evaluation import Evaluator
from worker.executor import Executor
from worker.main import create_worker


class LocalTrustedClient:
    def capabilities(self):
        return {"mode": "trusted", "arbitrary_code_enabled": False, "message": "Trusted only"}

    def evaluate(self, request):
        try:
            return Evaluator(Executor()).evaluate(request)
        except ValueError as exc:
            raise WorkerRejected(str(exc)) from exc


@pytest.fixture
def client(tmp_path):
    app = create_app(
        Settings(database_url=f"sqlite:///{tmp_path / 'api.db'}"), worker=LocalTrustedClient()
    )
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as c:
        yield c


def submit(client, variant="buggy", challenge="two-sum", **extras):
    c = REGISTRY[challenge]
    return client.post(
        "/api/submissions",
        json={
            "challenge_id": challenge,
            "code": getattr(c, variant if variant == "buggy" else "reference"),
            "variant": variant,
            **extras,
        },
    )


def test_submission_history_comparison_and_reports(client):
    bad = submit(client, label="<script>alert(1)</script>").json()
    good = submit(client, "reference").json()
    assert bad["passed"] < bad["total"]
    assert good["passed"] == good["total"]
    assert len(client.get("/api/submissions").json()) == 2
    assert len(client.get("/api/submissions?limit=1&offset=1").json()) == 1
    stats = client.get("/api/stats").json()
    assert stats["submissions"] == 2 and stats["fully_passing"] == 1
    comparison = client.get(f"/api/compare?left={bad['id']}&right={good['id']}").json()
    assert comparison["pass_rate_delta"] > 0
    assert (
        client.get("/api/submissions/" + good["id"]).json()["code"] == REGISTRY["two-sum"].reference
    )
    for fmt, marker in [
        ("json", b'"candidate_sha256"'),
        ("html", b"&lt;script&gt;"),
        ("pdf", b"%PDF"),
    ]:
        response = client.get(f"/api/submissions/{bad['id']}/report.{fmt}")
        assert response.status_code == 200
        assert marker in response.content
        assert "attachment" in response.headers["content-disposition"]
        if fmt == "json":
            assert json.loads(response.content)["id"] == bad["id"]
        if fmt == "html":
            assert "<script>alert(1)</script>" not in response.text
    assert client.get(f"/api/submissions/{bad['id']}/report.exe").status_code == 422
    other = submit(client, "reference", "find-duplicates").json()
    assert client.get(f"/api/compare?left={bad['id']}&right={other['id']}").status_code == 422


def test_arbitrary_edits_are_rejected(client):
    response = client.post(
        "/api/submissions",
        json={"challenge_id": "two-sum", "variant": "reference", "code": "print(123)"},
    )
    assert response.status_code == 422
    assert client.get("/api/submissions").json() == []
    assert (
        client.post(
            "/api/submissions", json={"challenge_id": "unknown", "code": "pass"}
        ).status_code
        == 404
    )


def test_worker_outage_is_explicit(tmp_path):
    class Offline:
        def capabilities(self):
            raise WorkerUnavailable("offline")

        def evaluate(self, request):
            raise WorkerUnavailable("offline")

    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'offline.db'}"), Offline())
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as c:
        assert c.get("/api/capabilities").status_code == 503
        assert submit(c).status_code == 503
        assert c.get("/api/submissions").json() == []


def test_worker_auth_and_trusted_boundary():
    with TestClient(create_worker()) as c:
        assert c.get("/capabilities").status_code == 401
        headers = {"X-Worker-Token": Settings().worker_token}
        assert c.get("/capabilities", headers=headers).json()["arbitrary_code_enabled"] is False
        r = c.post(
            "/evaluate",
            headers=headers,
            json={"challenge_id": "two-sum", "variant": "buggy", "code": "pass"},
        )
        assert r.status_code == 422
