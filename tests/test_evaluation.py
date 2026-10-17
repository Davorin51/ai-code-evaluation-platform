from unittest.mock import Mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from backend.app.challenges import CHALLENGES, REGISTRY, trusted_code
from backend.app.contracts import SubmissionRequest
from worker.evaluation import Evaluator, check_result, static_analysis, strict_equal
from worker.executor import Executor, InfrastructureError, bounded_process


def request(challenge, variant):
    return SubmissionRequest(
        challenge_id=challenge.id,
        variant=variant,
        code=trusted_code(challenge, variant),
        label=variant,
    )


@pytest.mark.parametrize("challenge", CHALLENGES, ids=lambda c: c.id)
def test_reference_passes_every_case(challenge):
    result = Evaluator(Executor()).evaluate(request(challenge, "reference"))
    assert result.passed == result.total == len(challenge.cases)
    assert result.reference_verified
    assert len(result.candidate_sha256) == 64
    assert all(c.duration_ms is not None and c.peak_rss_kib > 0 for c in result.cases)


@pytest.mark.parametrize("challenge", CHALLENGES, ids=lambda c: c.id)
def test_buggy_candidate_fails(challenge):
    result = Evaluator(Executor()).evaluate(request(challenge, "buggy"))
    assert result.passed < result.total
    assert any(c.error for c in result.cases)
    assert "wrong_output" in result.categories or "runtime_error" in result.categories


@pytest.mark.parametrize(
    "variant,category",
    [
        ("syntax-error", "syntax_error"),
        ("runtime-error", "runtime_error"),
        ("timeout", "resource_limit"),
    ],
)
def test_known_error_examples(variant, category):
    result = Evaluator(Executor()).evaluate(request(REGISTRY["two-sum"], variant))
    assert result.passed == 0
    assert category in result.categories or (
        variant == "timeout" and "timeout" in result.categories
    )


@pytest.mark.parametrize("variant", [None, "reference", "buggy", "../runner", "syntax-error"])
def test_trusted_mode_rejects_edits_before_starting_process(variant):
    executor = Mock(mode="trusted")
    with pytest.raises(ValueError):
        Evaluator(executor).evaluate(
            SubmissionRequest(
                challenge_id="two-sum", code="import os\nos.system('echo unsafe')", variant=variant
            )
        )
    executor.run.assert_not_called()
    executor.available.assert_not_called()


def test_unknown_challenge():
    with pytest.raises(ValueError):
        Evaluator(Executor()).evaluate(SubmissionRequest(challenge_id="missing", code="pass"))


def test_reference_failure_is_infrastructure_error():
    executor = Mock(mode="trusted")
    executor.run.return_value = {"kind": "ok", "value": None}
    with pytest.raises(InfrastructureError, match="Reference verification"):
        Evaluator(executor).evaluate(request(REGISTRY["two-sum"], "reference"))


def test_static_analysis_does_not_execute_source():
    findings, status = static_analysis("import definitely_missing_module\nx = undefined_name\n")
    assert status == "completed"
    assert {f["code"] for f in findings} >= {"F401", "F821"}
    assert all("filename" not in f for f in findings)


@given(st.lists(st.integers(), max_size=30))
def test_strict_json_equality_is_reflexive(values):
    assert strict_equal(values, list(values))
    assert not strict_equal(True, 1)
    assert not strict_equal({"x": False}, {"x": 0})


def test_missing_exception_and_bad_envelope():
    assert check_result({"kind": "ok", "value": 3}, {"raises": "ValueError"})[0] == "wrong_output"
    assert check_result({"kind": "invalid_output", "error": "large"}, 4) == (
        "invalid_output",
        "large",
    )


def test_docker_options_and_fail_closed(monkeypatch):
    executor = Executor("docker")
    flags = executor.docker_command("test")
    for flag in [
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--pids-limit=16",
        "--memory=128m",
        "--memory-swap=128m",
        "--user=65534:65534",
        "--security-opt=no-new-privileges:true",
    ]:
        assert flag in flags
    assert not any("socket" in f or f.startswith("--volume") for f in flags)
    monkeypatch.setattr("worker.executor.shutil.which", lambda _: None)
    with pytest.raises(InfrastructureError):
        executor.available()
    with pytest.raises(ValueError):
        Executor("unsafe")


def test_bounded_process_timeout_and_output_limit():
    # These are checked-in testing utilities, never user submissions.
    import sys

    _, _, error = bounded_process([sys.executable, "-c", "import time;time.sleep(3)"], {}, 0.1)
    assert error == "timeout"
    _, _, error = bounded_process(
        [sys.executable, "-c", 'import os;os.write(1,b"x"*100000)'], {}, 2
    )
    assert error == "output_limit"


@given(st.lists(st.integers(min_value=-100, max_value=100), max_size=30))
def test_duplicate_reference_matches_independent_counting_oracle(values):
    # Only the repository-owned reference is compiled in this offline property test.
    namespace = {}
    exec(REGISTRY["find-duplicates"].reference, namespace)
    expected = sorted({n for n in values if values.count(n) > 1})
    assert namespace["solve"](values) == expected
