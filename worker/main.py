import hmac
import os
import threading

from fastapi import Depends, FastAPI, Header, HTTPException

from backend.app.config import Settings
from backend.app.contracts import SubmissionRequest
from backend.app.limits import BodyLimitMiddleware
from worker.evaluation import Evaluator
from worker.executor import Executor, InfrastructureError


def create_worker(evaluator: Evaluator | None = None) -> FastAPI:
    settings = Settings()
    service = evaluator or Evaluator(
        Executor(
            os.getenv("ACE_EXECUTION_MODE", "trusted"),
            os.getenv("ACE_SANDBOX_IMAGE", "ace-sandbox:local"),
        )
    )
    lock = threading.BoundedSemaphore(1)

    def authenticate(x_worker_token: str = Header(default="")):
        if not hmac.compare_digest(x_worker_token, settings.worker_token):
            raise HTTPException(401, "Invalid worker token")

    app = FastAPI(
        title="Private execution worker",
        docs_url=None,
        redoc_url=None,
        dependencies=[Depends(authenticate)],
    )

    app.add_middleware(BodyLimitMiddleware)

    @app.get("/capabilities")
    def capabilities():
        try:
            service.executor.available()
        except InfrastructureError as exc:
            raise HTTPException(503, str(exc)) from exc
        return {
            "mode": service.executor.mode,
            "arbitrary_code_enabled": service.executor.mode == "docker",
            "message": "Trusted examples only. Edited or arbitrary code is rejected."
            if service.executor.mode == "trusted"
            else "Disposable Docker execution. Local use only; containers are not a public multi-tenant security boundary.",
        }

    @app.post("/evaluate")
    def evaluate(request: SubmissionRequest):
        if not lock.acquire(blocking=False):
            raise HTTPException(429, "Worker busy; retry later")
        try:
            return service.evaluate(request)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except InfrastructureError as exc:
            raise HTTPException(503, str(exc)) from exc
        finally:
            lock.release()

    return app


app = create_worker()
