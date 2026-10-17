"""Run against a real Compose stack, never mocked responses."""

import os
import time

import httpx

from backend.app.challenges import REGISTRY

mode = os.getenv("ACE_SMOKE_MODE", "trusted")
base = "http://127.0.0.1:8080/api"
with httpx.Client(base_url=base, timeout=60, trust_env=False) as client:
    client.get("/health").raise_for_status()
    for _attempt in range(40):
        try:
            if client.get("/capabilities").json().get("mode") == mode:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    else:
        raise RuntimeError("Expected worker mode did not become available")
    challenge = REGISTRY["two-sum"]
    result = client.post(
        "/submissions",
        json={
            "challenge_id": challenge.id,
            "variant": "reference",
            "code": challenge.reference + ("\n# Edited candidate\n" if mode == "docker" else ""),
        },
    )
    result.raise_for_status()
    data = result.json()
    assert data["passed"] == data["total"] == 5
    assert data["mode"] == mode
    assert client.get(f"/submissions/{data['id']}/report.pdf").content.startswith(b"%PDF")
    rejected = client.post(
        "/submissions", json={"challenge_id": challenge.id, "variant": "reference", "code": "pass"}
    )
    assert rejected.status_code == (422 if mode == "trusted" else 201)
    if mode == "docker":
        assert rejected.json()["passed"] == 0
print(f"Compose API, {mode} worker, database, PDF and rejected incorrect trust boundary verified.")
