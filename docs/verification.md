# Verification record

## Verified application source

[Successful CI run 39058989360](https://github.com/Davorin51/ai-code-evaluation-platform/actions/runs/39058989360)
checked source commit `6709c8bd760440c9388df0fd51b73e5c83aae902` on 17 October 2026.
The subsequent portfolio-evidence commit adds documentation/screenshots only.

| Check | Observed result |
| --- | --- |
| Backend on Python 3.11, 3.12, 3.13 | All three jobs passed; 53 non-Docker tests each |
| Local backend coverage, Python 3.12.14 | 93.55%; backend and worker modules, runner excluded |
| Ruff lint / formatting | Passed |
| Python sdist / wheel build | Passed |
| Frontend formatting, TypeScript and Vite build | Passed |
| Real-backend Playwright workflow | Passed in Chromium |
| Responsive views | Overview, Challenges, History and Compare checked at 375, 768 and 1440 px; no page overflow |
| Accessibility scan | Overview: zero axe WCAG 2/2.1 A/AA violations; not a whole-product certification |
| Docker isolation suite | 5 passed; no skips in required CI job |
| Default Compose stack | Built and started; API/worker/SQLite/PDF/trusted rejection smoke passed |
| Opt-in Docker worker Compose override | Built and started; edited candidate executed through real API; arbitrary invalid code produced failed tests |

Docker checks exercised non-root UID, absent socket in candidate containers, network
connection failure, root write denial, cgroup PID/memory settings, CPU-loop termination,
memory failure, bounded stdout, filesystem disposal and a full 3/5 buggy evaluation.
The private worker used Docker CLI 26.1.5 against Engine 28.0.4 in the observed CI run.

## Reproducible evidence

- `frontend/tests/platform.spec.ts` creates two actual submissions via the UI, checks 3/5
  and 5/5 outcomes, downloads PDF, compares saved solutions and reopens history.
- `docs/screenshots/` contains actual images from that successful job. Images were inspected
  at desktop, tablet and phone widths, plus workspace/failure and comparison views.
- `examples/reports/` contains six exports from real API/worker HTTP calls on the local
  Python 3.12.14 environment. They are separate runs from the screenshots, so timings differ.
- Reference and buggy code hashes are in the exported JSON/PDF/HTML. Failure inputs and
  expected outputs are retained; no accuracy, confidence or synthetic performance scores exist.
- Both PDFs were rendered and visually inspected, including embedded fonts, wrapping and pagination.

The local authoring environment has no Docker daemon, so its Docker tests were explicitly
skipped/deselected. Docker claims above refer to executed GitHub Actions jobs, not local
host execution. A deprecation warning about Starlette's httpx TestClient adapter is emitted
by the pinned dependency combination; all recorded checks passed.

## Known limits

Single local workspace, no user authentication, no durable job queue/cancellation, no
statistically controlled timing benchmark and no public multi-tenant security claim.
The runner's ordinary Python timing/RSS observations are not tamper-proof attestation.
The separately loaded Monaco chunk is approximately 2.3 MB uncompressed; Vite warns about
its size. It is lazily loaded on editor use and does not require an external CDN.
Read `SECURITY.md` before enabling arbitrary code.
