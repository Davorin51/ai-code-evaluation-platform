from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.challenges import CHALLENGES, REGISTRY
from backend.app.config import Settings
from backend.app.contracts import SubmissionRequest
from backend.app.main import create_app


@pytest.fixture
def api(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("ACE_DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    with TestClient(create_app(Settings(database_url=url))) as client:
        yield client


def test_health_challenges_and_empty_database(api):
    assert api.get("/api/health").json()["status"] == "ok"
    entries = api.get("/api/challenges").json()
    assert len(entries) == 8
    assert len({c["id"] for c in entries}) == 8
    assert api.get("/api/submissions").json() == []
    assert api.get("/api/stats").json()["average_execution_ms"] is None
    assert api.get("/api/challenges/not-found").status_code == 404
    assert api.get("/api/submissions/missing").status_code == 404
    assert api.get("/api/submissions?limit=0").status_code == 422
    assert api.post("/api/submissions", json={}).status_code == 422


@pytest.mark.parametrize("challenge", CHALLENGES, ids=lambda c: c.id)
def test_challenge_contract(challenge):
    assert challenge.reference and challenge.buggy != challenge.reference
    assert challenge.constraints and challenge.complexity
    assert any(c.hidden for c in challenge.cases)
    assert len(challenge.public()["examples"]) < len(challenge.cases)
    compile(challenge.reference, challenge.id, "exec")


@pytest.mark.parametrize("size", [20001, 20002, 30000])
def test_code_size_limit(size):
    code = "x" * size
    with pytest.raises(ValidationError):
        SubmissionRequest(challenge_id="two-sum", code=code)


def test_input_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        SubmissionRequest(challenge_id="two-sum", code="pass", execute_on_host=True)


def test_migration_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("ACE_DATABASE_URL", f"sqlite:///{tmp_path / 'migrations.db'}")
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert Path(tmp_path / "migrations.db").exists()


def test_registry():
    assert set(REGISTRY) == {c.id for c in CHALLENGES}
