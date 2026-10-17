"""Disposable interpreter entry point. Never imported by the web API.

In trusted mode the parent supplies only exact checked-in code. Arbitrary code
is accepted only when this script is already INSIDE a restricted container.
"""

import contextlib
import json
import resource
import sys
import time


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**2, 128 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    payload = json.load(sys.stdin)
    start = time.perf_counter_ns()
    namespace = {}
    # Suppress normal prints without allocating a StringIO of unbounded size.
    with open("/dev/null", "w") as sink:
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                exec(compile(payload["code"], "<candidate>", "exec"), namespace)
                answer = namespace["solve"](**payload["input"])
            result = {"kind": "ok", "value": answer}
        except SyntaxError as exc:
            result = {"kind": "syntax_error", "error": f"{exc.msg} (line {exc.lineno})"}
        except BaseException as exc:
            result = {
                "kind": "exception",
                "exception": type(exc).__name__,
                "error": str(exc)[:1000],
            }
    result["duration_ms"] = (time.perf_counter_ns() - start) / 1_000_000
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    try:
        message = json.dumps(result, allow_nan=False)
        if len(message.encode()) > 60000:
            raise ValueError("Output exceeds 60 KB")
    except (TypeError, ValueError, OverflowError) as exc:
        message = json.dumps({"kind": "invalid_output", "error": str(exc)[:1000]})
    print(message)


if __name__ == "__main__":
    main()
