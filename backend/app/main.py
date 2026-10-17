import logging
import threading
from contextlib import asynccontextmanager
from datetime import UTC
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.challenges import CHALLENGES, REGISTRY
from backend.app.config import Settings
from backend.app.contracts import SubmissionRequest
from backend.app.database import Submission, database
from backend.app.limits import BodyLimitMiddleware
from backend.app.logging import configure_logging
from backend.app.transport import WorkerClient, WorkerRejected, WorkerUnavailable


def serialize(row: Submission, detail: bool = True) -> dict:
    data = {
        "id": row.id,
        "challenge_id": row.challenge_id,
        "label": row.label,
        "origin": row.origin,
        "created_at": row.created_at.replace(tzinfo=UTC).isoformat(),
        "passed": row.result["passed"],
        "total": row.result["total"],
        "pass_rate": row.result["pass_rate"],
        "mode": row.result["mode"],
        "execution_ms": row.result["execution_ms"],
    }
    if detail:
        data.update(code=row.code, result=row.result)
    return data


def create_app(settings: Settings | None = None, worker=None) -> FastAPI:
    settings = settings or Settings()
    engine, sessions = database(settings.database_url)
    client = worker or WorkerClient(settings)
    slots = threading.BoundedSemaphore(2)

    @asynccontextmanager
    async def lifespan(app):
        configure_logging()
        yield
        engine.dispose()

    app = FastAPI(title="AI Code Evaluation Platform", version="0.1.0", lifespan=lifespan)
    app.add_middleware(BodyLimitMiddleware)

    app.state.engine = engine
    app.state.sessions = sessions

    def session():
        with sessions() as db:
            yield db

    DB = Annotated[Session, Depends(session)]

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/capabilities")
    def capabilities():
        try:
            return client.capabilities()
        except WorkerUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/api/challenges")
    def challenges():
        return [challenge.public() for challenge in CHALLENGES]

    @app.get("/api/challenges/{challenge_id}")
    def challenge(challenge_id: str):
        if challenge_id not in REGISTRY:
            raise HTTPException(404, "Challenge not found")
        return REGISTRY[challenge_id].public()

    @app.post("/api/submissions", status_code=201)
    def submit(request: SubmissionRequest, db: DB):
        if request.challenge_id not in REGISTRY:
            raise HTTPException(404, "Challenge not found")
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Two evaluations already running; retry after completion")
        try:
            result = client.evaluate(request)
            row = Submission(
                challenge_id=request.challenge_id,
                label=request.label,
                origin=request.origin,
                code=request.code,
                result=result.model_dump(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            logging.getLogger("code_eval.api").info(
                "evaluation_saved id=%s challenge=%s passed=%s/%s",
                row.id,
                row.challenge_id,
                result.passed,
                result.total,
            )
            return serialize(row)
        except WorkerRejected as exc:
            raise HTTPException(422, str(exc)) from exc
        except WorkerUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        finally:
            slots.release()

    @app.get("/api/submissions")
    def history(db: DB, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        rows = db.scalars(
            select(Submission)
            .order_by(Submission.created_at.desc(), Submission.id)
            .limit(limit)
            .offset(offset)
        )
        return [serialize(row, False) for row in rows]

    def find(db, ident):
        row = db.get(Submission, ident)
        if row is None:
            raise HTTPException(404, "Submission not found")
        return row

    @app.get("/api/submissions/{submission_id}")
    def detail(submission_id: str, db: DB):
        return serialize(find(db, submission_id))

    @app.get("/api/stats")
    def stats(db: DB):
        # Aggregate actual stored results; no invented or cached example metrics.
        rows = list(db.scalars(select(Submission)))
        return {
            "submissions": len(rows),
            "fully_passing": sum(r.result["passed"] == r.result["total"] for r in rows),
            "tests_passed": sum(r.result["passed"] for r in rows),
            "tests_run": sum(r.result["total"] for r in rows),
            "average_execution_ms": sum(r.result["execution_ms"] for r in rows) / len(rows)
            if rows
            else None,
        }

    @app.get("/api/compare")
    def compare(left: str, right: str, db: DB):
        a, b = find(db, left), find(db, right)
        if a.challenge_id != b.challenge_id:
            raise HTTPException(422, "Choose two submissions for the same challenge")
        return {
            "left": serialize(a),
            "right": serialize(b),
            "pass_rate_delta": b.result["pass_rate"] - a.result["pass_rate"],
            "timing_note": "Single-run timings include interpreter work, exclude container startup, and are not a statistically controlled speed benchmark.",
        }

    @app.get("/api/submissions/{submission_id}/report.{format}")
    def report(submission_id: str, format: str, db: DB):
        from backend.app.reporting import render_report

        if format not in {"json", "html", "pdf"}:
            raise HTTPException(422, "Report format must be json, html or pdf")
        content, media = render_report(serialize(find(db, submission_id)), format)
        return Response(
            content,
            media_type=media,
            headers={
                "Content-Disposition": f'attachment; filename="evaluation-{submission_id}.{format}"',
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
                "X-Content-Type-Options": "nosniff",
            },
        )

    return app


app = create_app()
