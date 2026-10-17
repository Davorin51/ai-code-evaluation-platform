# Execution threat model

This is a **localhost portfolio application**, not a public code-execution service.
Do not submit secrets, credentials, proprietary tasks or personal datasets.
The API has no user accounts and grants local users access to all saved sources/reports.

## Default: trusted examples only

The private worker compares submitted source byte-for-byte with a selected checked-in
example. Unknown variants or even a one-character modification are rejected BEFORE any
candidate interpreter starts. This is an explicit allowlist, not AST filtering. Only these
reviewed examples run in a separate subprocess on the local host or trusted worker container.
Resource limits protect against the deliberately included infinite-loop example; they do
not turn an unrestricted host subprocess into a sandbox. Arbitrary code never takes this path.
The API only communicates with the worker and never imports submitted modules.

## Opt-in Docker path

Run on a disposable/dedicated Linux VM with cgroup v2 and Docker's default seccomp enabled.
A compromised worker with daemon access could control that Docker host. The Compose override
mounts the socket into the PRIVATE worker only and gives its non-root account the socket
GID. A read-only socket mount would not remove daemon power, so it is not represented as such.
API and frontend never get the socket, Docker credentials or host filesystem mounts.

Each candidate test uses a fresh container: UID/GID 65534, no network, read-only root,
capabilities dropped, no-new-privileges, 128 MiB memory and equal memory+swap limit,
16 PIDs, 0.5 CPU quota, one CPU-second soft/hard limit, three-second wall deadline,
32 open files, no core dumps, 16 MiB noexec/nosuid/nodev tmpfs and 64 KiB output budget.
No source/input directory, secrets, Docker socket or expected outputs are mounted.
The image contains only Python and the runner. Source/input arrive via stdin.
The parent removes the named container in a finally block, including on timeout.
If the daemon is unavailable, no candidate is run on the host as a fallback.

The Linux resource module adds address-space/CPU/file limits inside both runner modes.
CPU termination and OOM can be indistinguishable: reports label the category resource_limit
rather than guessing an exact cause. A container cleanup failure after daemon loss needs
operator attention (`docker ps --filter name=ace-` on the disposable VM).

## What this does not guarantee

Docker shares a kernel. It does not defend against all kernel/runtime vulnerabilities.
No claim of safe internet-facing multi-tenant execution is made. Add microVM/VM isolation,
authentication, quotas, request scheduling, cancellation, per-user storage and security
review before public hosting. Do not publish worker port 8001. Keep the Compose frontend's
127.0.0.1 binding unless an authenticated reverse proxy and stronger deployment controls exist.

An adversarial program can interfere with its own Python instrumentation/output protocol.
Expected answers remain outside the process, but the runner is not tamper-proof against
self-introspecting code. Timing/RSS are runner observations for ordinary review, not trusted
attestation. No relative performance conclusion is drawn from a single run.

Hidden tests are a debugging convenience: the local project includes all test definitions,
reference code and post-run failure inputs. This is deliberately not a secret hiring exam.

## Other boundaries

- 128 KiB HTTP body cap, 20,000-character source limit, validated request schemas.
- Private worker token checked with constant-time comparison; environment configured.
- One active worker evaluation, two API evaluation slots per API process. No distributed queue.
- SQLite contains candidate code and output. Protect/delete the database according to your needs.
- HTML escapes user-controlled strings, is downloaded as an attachment and has restrictive CSP.
- PDF text escapes ReportLab markup. Reports and logs do not execute candidate Python.
- No model APIs, telemetry integration, external editor CDN or paid services are used by the app.
- Ruff is a static checker, not a security sandbox or correctness proof.

To report an issue, open a GitHub issue with a minimal non-sensitive reproduction.
