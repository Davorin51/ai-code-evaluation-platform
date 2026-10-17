import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

RUNNER = Path(__file__).with_name("runner.py")
LIMITS = {
    "wall_seconds_per_case": 3,
    "cpu_seconds_per_case": 1,
    "memory_mib": 128,
    "output_bytes": 65536,
    "docker_pids": 16,
    "network": "none",
}


class InfrastructureError(Exception):
    pass


def bounded_process(
    command: list[str], payload: dict, timeout: float
) -> tuple[bytes, int, str | None]:
    """Bound output while streaming; don't accumulate an unlimited communicate()."""
    with tempfile.TemporaryFile() as incoming:
        incoming.write(json.dumps(payload).encode())
        incoming.seek(0)
        process = subprocess.Popen(
            command,
            stdin=incoming,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env={"PATH": os.defpath, "HOME": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"},
        )
        collected = bytearray()
        error = None
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, True)
            selector.register(process.stderr, selectors.EVENT_READ, False)
            try:
                while selector.get_map():
                    if time.monotonic() > deadline:
                        error = "timeout"
                        break
                    for key, _ in selector.select(timeout=0.05):
                        chunk = os.read(key.fileobj.fileno(), 4096)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        # stderr shares the same budget but is not part of JSON.
                        collected.extend(chunk if key.data else b" " * len(chunk))
                        if len(collected) > LIMITS["output_bytes"]:
                            error = "output_limit"
                            break
                    if error:
                        break
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                process.stdout.close()
                process.stderr.close()
        return bytes(collected), process.returncode, error


class Executor:
    def __init__(self, mode: str = "trusted", image: str = "ace-sandbox:local"):
        if mode not in {"trusted", "docker"}:
            raise ValueError("Execution mode must be trusted or docker")
        self.mode, self.image = mode, image

    def docker_command(self, name: str) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--pull=never",
            "--network=none",
            "--user=65534:65534",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--pids-limit=16",
            "--memory=128m",
            "--memory-swap=128m",
            "--cpus=0.5",
            "--ulimit=cpu=1:1",
            "--ulimit=nofile=32:32",
            "--ulimit=core=0:0",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m",
            "--log-driver=none",
            "-i",
            self.image,
        ]

    def available(self):
        if self.mode == "docker":
            if not shutil.which("docker"):
                raise InfrastructureError(
                    "Docker CLI is missing; arbitrary execution remains disabled"
                )
            try:
                subprocess.run(
                    ["docker", "image", "inspect", self.image],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )
            except (subprocess.SubprocessError, OSError) as exc:
                raise InfrastructureError(
                    "Sandbox image/daemon unavailable; no host execution fallback"
                ) from exc

    def run(self, code: str, case_input: dict[str, Any]) -> dict:
        name = "ace-" + uuid.uuid4().hex
        command = (
            self.docker_command(name)
            if self.mode == "docker"
            else [sys.executable, "-I", str(RUNNER)]
        )
        try:
            output, returncode, error = bounded_process(
                command, {"code": code, "input": case_input}, LIMITS["wall_seconds_per_case"]
            )
            if error:
                return {
                    "kind": error,
                    "error": "Per-case wall time exceeded"
                    if error == "timeout"
                    else "Output limit exceeded",
                }
            if returncode in {-signal.SIGXCPU, -signal.SIGKILL, 137, 152}:
                return {
                    "kind": "resource_limit",
                    "error": "CPU or memory limit terminated the process",
                }
            if returncode != 0:
                if self.mode == "docker" and returncode in {125, 126, 127}:
                    raise InfrastructureError("Docker could not start the sandbox")
                return {"kind": "runtime_error", "error": f"Process exited with code {returncode}"}
            try:
                result = json.loads(output)
                if not isinstance(result, dict) or result.get("kind") not in {
                    "ok",
                    "exception",
                    "syntax_error",
                    "invalid_output",
                }:
                    raise ValueError("Unexpected runner envelope")
                return result
            except (ValueError, UnicodeError) as exc:
                return {
                    "kind": "invalid_output",
                    "error": f"Invalid runner output: {type(exc).__name__}",
                }
        except OSError as exc:
            raise InfrastructureError("Execution process could not start") from exc
        finally:
            if self.mode == "docker":
                # Kill the container even when the client was killed or lost contact.
                try:
                    subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
                except (OSError, subprocess.SubprocessError):
                    pass
