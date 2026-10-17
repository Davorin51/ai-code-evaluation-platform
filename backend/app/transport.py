import httpx

from backend.app.config import Settings
from backend.app.contracts import EvaluationResult, SubmissionRequest


class WorkerUnavailable(Exception):
    pass


class WorkerRejected(Exception):
    pass


class WorkerClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _call(self, method: str, path: str, payload: dict | None = None) -> dict:
        try:
            response = httpx.request(
                method,
                self.settings.worker_url + path,
                json=payload,
                headers={"X-Worker-Token": self.settings.worker_token},
                timeout=self.settings.request_timeout,
                trust_env=False,
            )
            if response.status_code == 422:
                raise WorkerRejected(
                    "Worker rejected this candidate. Trusted mode accepts only exact bundled examples."
                )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WorkerUnavailable(
                "Execution worker unavailable; no candidate code was executed by the API."
            ) from exc

    def capabilities(self) -> dict:
        return self._call("GET", "/capabilities")

    def evaluate(self, request: SubmissionRequest) -> EvaluationResult:
        return EvaluationResult.model_validate(
            self._call("POST", "/evaluate", request.model_dump())
        )
