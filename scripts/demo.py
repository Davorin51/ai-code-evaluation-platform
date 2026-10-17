"""Export actual API results. Start the separate worker and API before running."""

import json
from pathlib import Path

import httpx

from backend.app.challenges import REGISTRY

output = Path("examples/reports")
output.mkdir(parents=True, exist_ok=True)
challenge = REGISTRY["two-sum"]
with httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=120, trust_env=False) as client:
    for variant in ("buggy", "reference"):
        response = client.post(
            "/submissions",
            json={
                "challenge_id": challenge.id,
                "variant": variant,
                "code": getattr(challenge, variant),
                "label": "Buggy example" if variant == "buggy" else "Corrected reference",
                "origin": "trusted-example",
            },
        )
        response.raise_for_status()
        data = response.json()
        for format in ("json", "html", "pdf"):
            report = client.get(f"/submissions/{data['id']}/report.{format}")
            report.raise_for_status()
            (output / f"two-sum-{variant}.{format}").write_bytes(report.content)
        print(
            json.dumps(
                {
                    "id": data["id"],
                    "variant": variant,
                    "passed": data["passed"],
                    "total": data["total"],
                }
            )
        )
