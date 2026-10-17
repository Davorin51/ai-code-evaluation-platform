"""Real isolation checks; never fall back to the host when Docker is missing."""

import os
import shutil

import pytest

from worker.executor import Executor

pytestmark = pytest.mark.docker


@pytest.fixture
def sandbox():
    executor = Executor("docker")
    if not shutil.which("docker") and not os.getenv("ACE_REQUIRE_DOCKER"):
        pytest.skip("Docker is unavailable; isolation has not been verified here")
    executor.available()
    return executor


def test_security_boundary_inside_real_container(sandbox):
    code = """def solve():
    import os, pathlib, socket
    facts = {"uid": os.getuid(), "socket_mounted": pathlib.Path("/var/run/docker.sock").exists(),
             "pids": pathlib.Path("/sys/fs/cgroup/pids.max").read_text().strip(),
             "memory": pathlib.Path("/sys/fs/cgroup/memory.max").read_text().strip()}
    try:
        pathlib.Path("/forbidden").write_text("bad")
        facts["root_read_only"] = False
    except OSError:
        facts["root_read_only"] = True
    try:
        socket.create_connection(("1.1.1.1",53), timeout=0.2)
        facts["network_blocked"] = False
    except OSError:
        facts["network_blocked"] = True
    return facts
"""
    result = sandbox.run(code, {})
    assert result["kind"] == "ok", result
    assert result["value"] == {
        "uid": 65534,
        "socket_mounted": False,
        "pids": "16",
        "memory": "134217728",
        "root_read_only": True,
        "network_blocked": True,
    }


def test_infinite_loop_is_terminated(sandbox):
    result = sandbox.run("def solve():\n    while True:\n        pass\n", {})
    assert result["kind"] in {"timeout", "resource_limit"}


def test_memory_and_output_limits(sandbox):
    result = sandbox.run("def solve():\n    return bytearray(256 * 1024**2)\n", {})
    assert result["kind"] in {"exception", "resource_limit"}
    if result["kind"] == "exception":
        assert result["exception"] == "MemoryError"
    result = sandbox.run(
        'def solve():\n    import os\n    while True:\n        os.write(1,b"x"*8192)\n', {}
    )
    assert result["kind"] == "output_limit"


def test_file_is_not_retained_between_cases(sandbox):
    assert (
        sandbox.run(
            'def solve():\n    open("/tmp/candidate-marker","w").write("one")\n    return True\n',
            {},
        )["value"]
        is True
    )
    assert (
        sandbox.run(
            'def solve():\n    import os\n    return os.path.exists("/tmp/candidate-marker")\n', {}
        )["value"]
        is False
    )
