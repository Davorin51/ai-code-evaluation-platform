# Architecture and evaluation contracts

## Request lifecycle

1. React loads challenge contracts and worker capabilities from the API. Until Docker
   availability is confirmed, arbitrary editing remains disabled.
2. FastAPI validates the request, bounds concurrency and calls the private worker over HTTP.
3. Trusted mode resolves a repository-owned variant and requires exact source equality.
   Docker mode first verifies that the local sandbox image exists; runtime pull is disabled.
4. The worker runs Ruff using an isolated config and a temporary source file. Ruff never
   imports the file. Findings/unavailability are independent from correctness.
5. For EACH test, a fresh reference execution is checked against the expected fixture.
   A reference mismatch is an infrastructure error; no misleading candidate verdict is saved.
6. A fresh candidate execution receives source and input, but no expected output. The worker
   compares primitive/list/dict JSON values with strict types (True is not integer 1).
   Explicit expected exceptions are matched by exception class name.
7. The worker returns structured results, source SHA-256, runner/challenge version and limits.
8. The API commits a completed evaluation to SQLite. Failed worker/infrastructure requests
   return 503 and do not create fake successful history entries. Busy API/worker requests
   return a capacity error. API transport maps non-422 worker HTTP failures to 503.
9. JSON/HTML/PDF reports derive from the exact persisted result, not regenerated measurements.

## Modules and dependency boundaries

`backend.app.main` knows only the worker HTTP client and Pydantic contracts; it does not
import the executor. Tests inject a deterministic local client to exercise database/API logic.
Networked E2E/Compose tests use the real separate worker. No shared Docker socket is needed
in default mode. `worker.runner` uses only standard-library modules in a disposable process.

SQLite schema changes use Alembic; the API never silently calls create_all on startup.
Tests create fresh databases. Compose runs `alembic upgrade head` once before API startup.
Synchronous execution is intentionally simple: one worker evaluation at a time; no claims
of durable jobs, cancellation or horizontal scaling. History endpoint supports limit/offset.
The dashboard displays the latest 50 rows; aggregate statistics use all locally stored rows.

## Failure categories

- `syntax_error`: Python compilation fails.
- `runtime_error`: unexpected exception or abnormal interpreter exit.
- `wrong_output`: JSON value/type mismatch or missing expected exception.
- `timeout`: the parent wall-clock deadline expires.
- `resource_limit`: CPU/memory-related signal terminates the process; exact cause may be unknown.
- `output_limit`: captured output exceeds the bounded budget.
- `invalid_output`: result is not JSON serializable or the runner envelope is invalid.
- Infrastructure errors (missing daemon/image, failed reference, worker unreachable) are 503.

## Measurements

Successful/completed runner cases measure compilation plus call work using perf_counter_ns.
Container/interpreter startup and worker scheduling are excluded. Peak RSS is process-wide,
includes the interpreter and uses Linux KiB. Failure before a completed response has null
measurements; the displayed sum includes completed cases only. Reference timing is another
single run, not a controlled speedup benchmark. No confidence score or code-coverage estimate
is derived from deterministic case counts. Pytest implementation coverage is reported separately.

The challenge format is a frozen dataclass containing original problem text, constraints,
reference/buggy source and versioned deterministic cases. Public browsing omits edge-case
inputs; completed reports reveal them for reproducible debugging. References, fixtures and
sample reports are all available in source, so this is not a secret assessment platform.
