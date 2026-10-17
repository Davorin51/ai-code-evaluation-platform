"""Run against a real Compose stack, never mocked responses."""

import httpx

from backend.app.challenges import REGISTRY

base = "http://127.0.0.1:8080/api"
with httpx.Client(base_url=base, timeout=60, trust_env=False) as client:
    client.get("/health").raise_for_status()
    assert client.get("/capabilities").json()["mode"] == "trusted"
    challenge = REGISTRY["two-sum"]
    result = client.post(
        "/submissions",
        json={"challenge_id": challenge.id, "variant": "reference", "code": challenge.reference},
    )
    result.raise_for_status()
    data = result.json()
    assert data["passed"] == data["total"] == 5
    assert client.get(f"/submissions/{data['id']}/report.pdf").content.startswith(b"%PDF")
    rejected = client.post(
        "/submissions", json={"challenge_id": challenge.id, "variant": "reference", "code": "pass"}
    )
    assert rejected.status_code == 422
print("Compose API, worker, database, PDF and trusted-only boundary verified.")
