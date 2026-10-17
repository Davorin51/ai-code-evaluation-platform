from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z-]+$")
    code: str = Field(min_length=1, max_length=20000)
    variant: str | None = Field(default=None, max_length=50)
    label: str = Field(default="Candidate solution", min_length=1, max_length=100)
    origin: Literal["manual", "ai-generated", "trusted-example"] = "manual"


class CaseResult(BaseModel):
    name: str
    hidden: bool
    status: str
    input: dict[str, Any]
    expected: Any
    actual: Any = None
    error: str | None = None
    duration_ms: float | None = None
    peak_rss_kib: int | None = None
    reference_duration_ms: float | None = None


class EvaluationResult(BaseModel):
    mode: Literal["trusted", "docker"]
    cases: list[CaseResult]
    passed: int
    total: int
    pass_rate: float
    categories: list[str]
    static_findings: list[dict[str, Any]]
    static_status: str
    execution_ms: float
    summary: str
    reference_verified: bool
    challenge_version: str = "1"
    runner_version: str = "1"
    candidate_sha256: str
    runtime: str
    limits: dict[str, Any]
