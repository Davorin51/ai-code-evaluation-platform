import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from backend.app.challenges import REGISTRY, trusted_code
from backend.app.contracts import CaseResult, EvaluationResult, SubmissionRequest
from worker.executor import LIMITS, Executor, InfrastructureError


def strict_equal(left, right) -> bool:
    """JSON equality that does not treat True as 1 or allow NaN."""
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(
            strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(strict_equal(left[k], right[k]) for k in left)
    return left == right


def check_result(outcome: dict, expected) -> tuple[str, str | None]:
    if isinstance(expected, dict) and set(expected) == {"raises"}:
        if outcome.get("kind") == "exception" and outcome.get("exception") == expected["raises"]:
            return "passed", None
        return "wrong_output", f"Expected {expected['raises']} to be raised"
    if outcome.get("kind") == "exception":
        return "runtime_error", f"{outcome.get('exception')}: {outcome.get('error')}"
    if outcome.get("kind") != "ok":
        return outcome.get("kind", "invalid_output"), outcome.get("error", "Runner failed")
    if not strict_equal(outcome.get("value"), expected):
        return "wrong_output", "Returned value differs from the challenge contract"
    return "passed", None


def static_analysis(code: str) -> tuple[list[dict], str]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "candidate.py"
        path.write_text(code)
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--isolated",
                    "--no-cache",
                    "--select",
                    "E4,E7,E9,F,B",
                    "--output-format",
                    "json",
                    str(path),
                ],
                capture_output=True,
                timeout=5,
            )
            if completed.returncode not in {0, 1}:
                return [], "unavailable"
            findings = json.loads(completed.stdout)
            # Do not leak the worker's temporary filesystem path.
            return [
                {k: item.get(k) for k in ("code", "message", "location", "end_location")}
                for item in findings
            ], "completed"
        except (OSError, subprocess.SubprocessError, ValueError):
            return [], "unavailable"


class Evaluator:
    def __init__(self, executor: Executor):
        self.executor = executor

    def evaluate(self, request: SubmissionRequest) -> EvaluationResult:
        challenge = REGISTRY.get(request.challenge_id)
        if challenge is None:
            raise ValueError("Unknown challenge")
        if self.executor.mode == "trusted":
            # This equality check is the security boundary for local demo mode.
            # No user modifications, AST allowlists or inferred trust are accepted.
            if request.code != trusted_code(challenge, request.variant):
                raise ValueError("Trusted mode permits only exact bundled examples")
        self.executor.available()
        findings, static_status = static_analysis(request.code)
        cases = []
        for case in challenge.cases:
            reference = self.executor.run(challenge.reference, case.input)
            status, _ = check_result(reference, case.expected)
            if status != "passed":
                raise InfrastructureError(f"Reference verification failed for {case.name}")
            outcome = self.executor.run(request.code, case.input)
            status, error = check_result(outcome, case.expected)
            cases.append(
                CaseResult(
                    name=case.name,
                    hidden=case.hidden,
                    input=case.input,
                    expected=case.expected,
                    actual=outcome.get("value"),
                    status=status,
                    error=error,
                    duration_ms=outcome.get("duration_ms"),
                    peak_rss_kib=outcome.get("peak_rss_kib"),
                    reference_duration_ms=reference.get("duration_ms"),
                )
            )
        passed = sum(case.status == "passed" for case in cases)
        categories = sorted({case.status for case in cases if case.status != "passed"})
        summary = (
            f"{passed}/{len(cases)} deterministic tests passed. "
            "Test pass rate is not code coverage or proof of general correctness. "
            + (
                "All reference checks passed."
                if not categories
                else "Review the reproducible failures below."
            )
        )
        return EvaluationResult(
            mode=self.executor.mode,
            cases=cases,
            passed=passed,
            total=len(cases),
            pass_rate=100 * passed / len(cases),
            categories=categories,
            static_findings=findings,
            static_status=static_status,
            execution_ms=sum(case.duration_ms or 0 for case in cases),
            summary=summary,
            reference_verified=True,
            candidate_sha256=hashlib.sha256(request.code.encode()).hexdigest(),
            runtime=f"CPython {platform.python_version()}"
            if self.executor.mode == "trusted"
            else "sandbox image: " + self.executor.image_identity,
            limits={
                **LIMITS,
                "scope": "per test; RSS includes interpreter; Linux KiB; time excludes container startup",
            },
        )
