"""Tests for Feature #44 — mcp-server Docker Image (docker/Dockerfile.mcp).

SRS: FR-028: mcp-server Docker Image [Wave 4]

All tests are Docker integration tests and require a running Docker daemon.
They are marked @pytest.mark.real and use a session-scoped fixture that builds
the image once and tears it down after all tests complete.

Test layers:
  [integration] — Docker daemon required; builds and inspects codecontext-mcp-test image

Security: N/A — Dockerfile is a declarative build spec with no user-facing input surface.
"""

# [mutation-exempt] — Dockerfile-only feature (docker/Dockerfile.mcp); zero Python src/ code added.
# Mutation testing (mutmut) is N/A: no Python source to mutate. All test assertions verify
# Docker behavior via subprocess; mutmut sandbox (mutants/) cannot run Docker integration tests.
#
# 2026-05-06 update: now includes runtime E2E (T-13 detached-stays-running, T-14 git available,
# T-15 streamable-http MCP initialize handshake) — see test docstrings for traceability.

from __future__ import annotations

import json
import socket
import subprocess
import time

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMAGE_TAG = "codecontext-mcp-test"
DOCKERFILE_PATH = "docker/Dockerfile.mcp"


# ---------------------------------------------------------------------------
# Helper: docker inspect
# ---------------------------------------------------------------------------


def docker_inspect(image_name: str) -> dict:
    """Run docker inspect on an image and return the parsed JSON (first element)."""
    result = subprocess.run(
        ["docker", "inspect", image_name],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)[0]


# ---------------------------------------------------------------------------
# Session-scoped fixture: build image once, clean up after session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def built_mcp_image():
    """Build docker/Dockerfile.mcp once for the session; remove image on teardown.

    feature-44
    """
    result = subprocess.run(
        [
            "docker",
            "build",
            "-f",
            DOCKERFILE_PATH,
            "-t",
            IMAGE_TAG,
            ".",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Image build failed (rc={result.returncode}):\n{result.stderr}"
    )
    yield IMAGE_TAG
    # Teardown: remove the test image
    subprocess.run(["docker", "rmi", "-f", IMAGE_TAG], capture_output=True)


# ===========================================================================
# T-01: Build exits 0 and image is present
# ===========================================================================


@pytest.mark.real
def test_t01_build_succeeds():
    """T-01: docker build with Dockerfile.mcp exits 0 and produces the image.

    feature-44
    Traces: VS-1, FR-028 AC-1
    Kills bug: Missing Dockerfile entirely.
    """
    result = subprocess.run(
        [
            "docker",
            "build",
            "-f",
            DOCKERFILE_PATH,
            "-t",
            IMAGE_TAG,
            ".",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Build exited with {result.returncode}.\nSTDERR:\n{result.stderr}"
    )
    # Verify image is now listed
    ls_result = subprocess.run(
        ["docker", "image", "inspect", IMAGE_TAG],
        capture_output=True,
        text=True,
    )
    assert ls_result.returncode == 0, "Image not found in local registry after build"


# ===========================================================================
# T-02: CMD is exec-form ["python", "-m", "src.query.mcp_server"]
# ===========================================================================


@pytest.mark.real
def test_t02_cmd_is_mcp_server(built_mcp_image):
    """T-02: Image CMD equals ["python", "-m", "src.query.mcp_server"] (exec-form).

    feature-44
    Traces: VS-2, FR-028 AC-2
    Kills bug: Wrong CMD (shell-form, wrong module path, etc.)
    """
    info = docker_inspect(built_mcp_image)
    cmd = info["Config"]["Cmd"]
    assert cmd == ["python", "-m", "src.query.mcp_server"], (
        f"Expected CMD ['python', '-m', 'src.query.mcp_server'], got: {cmd}"
    )


# ===========================================================================
# T-03: HEALTHCHECK probes the streamable-http TCP listener on port 3000
# ===========================================================================


@pytest.mark.real
def test_t03_healthcheck_uses_socket_probe(built_mcp_image):
    """T-03: Image HEALTHCHECK.Test probes localhost:3000 with socket.create_connection.

    feature-44
    Traces: VS-3, FR-028 AC-3
    Kills bug: HEALTHCHECK still uses pgrep (which is absent from python:3.11-slim).
    """
    info = docker_inspect(built_mcp_image)
    healthcheck = info["Config"].get("Healthcheck", {})
    assert healthcheck, "No HEALTHCHECK defined in image config"
    test_cmd = healthcheck.get("Test", [])
    assert test_cmd, "HEALTHCHECK.Test is empty"
    full_cmd = " ".join(test_cmd)
    assert "socket.create_connection" in full_cmd, (
        f"HEALTHCHECK does not use socket probe: {test_cmd}"
    )
    assert "3000" in full_cmd, (
        f"HEALTHCHECK does not reference port 3000: {test_cmd}"
    )
    assert "pgrep" not in full_cmd, (
        f"HEALTHCHECK still references pgrep (procps not in slim image): {test_cmd}"
    )


# ===========================================================================
# T-04: Dev packages (pytest, mutmut, locust) NOT installed
# ===========================================================================


@pytest.mark.real
def test_t04_no_dev_packages_installed(built_mcp_image):
    """T-04: Image does not contain dev packages (pytest, mutmut, locust).

    feature-44
    Traces: VS-4, FR-028 AC-4
    Kills bug: Accidental pip install .[dev] in Dockerfile.
    """
    result = subprocess.run(
        ["docker", "run", "--rm", built_mcp_image, "pip", "list"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"pip list failed: {result.stderr}"
    installed_packages = result.stdout.lower()
    for dev_pkg in ("pytest", "mutmut", "locust"):
        assert dev_pkg not in installed_packages, (
            f"Dev package '{dev_pkg}' found in image — should not be installed"
        )


# ===========================================================================
# T-05: Runtime user is appuser (non-root)
# ===========================================================================


@pytest.mark.real
def test_t05_runtime_user_is_appuser(built_mcp_image):
    """T-05: Image Config.User is 'appuser' or '1000' (non-root).

    feature-44
    Traces: VS-4, FR-028 AC-4
    Kills bug: Missing USER appuser instruction.
    """
    info = docker_inspect(built_mcp_image)
    user = info["Config"].get("User", "")
    assert user in ("appuser", "1000"), (
        f"Expected User=appuser or 1000, got: '{user}'"
    )


# ===========================================================================
# T-06: Build fails when Dockerfile.mcp is absent
# ===========================================================================


@pytest.mark.real
def test_t06_build_fails_without_dockerfile(tmp_path):
    """T-06: docker build exits non-zero when Dockerfile.mcp does not exist.

    feature-44
    Traces: §Algorithm Error Handling: Dockerfile.mcp absent
    Kills bug: Test passes even when Dockerfile is missing (wrong setup).
    """
    result = subprocess.run(
        [
            "docker",
            "build",
            "-f",
            str(tmp_path / "Dockerfile.nonexistent"),
            "-t",
            "codecontext-mcp-test-shouldfail",
            ".",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "Expected build to fail with non-existent Dockerfile, but it succeeded"
    )
    error_output = result.stderr + result.stdout
    assert any(
        phrase in error_output.lower()
        for phrase in ("no such file", "unable to prepare context", "does not exist", "not found")
    ), f"Expected file-not-found error message, got:\n{error_output}"


# ===========================================================================
# T-07: HEALTHCHECK interval=30s, timeout=5s, retries=3
# ===========================================================================


@pytest.mark.real
def test_t07_healthcheck_timing_values(built_mcp_image):
    """T-07: HEALTHCHECK interval=30s (30e9 ns), timeout=5s (5e9 ns), retries=3.

    feature-44
    Traces: §Algorithm Boundary: HEALTHCHECK interval/timeout
    Kills bug: Wrong interval/timeout values.
    """
    info = docker_inspect(built_mcp_image)
    hc = info["Config"].get("Healthcheck", {})
    assert hc, "No HEALTHCHECK defined"
    assert hc.get("Interval") == 30_000_000_000, (
        f"Expected Interval=30000000000 ns (30s), got {hc.get('Interval')}"
    )
    assert hc.get("Timeout") == 5_000_000_000, (
        f"Expected Timeout=5000000000 ns (5s), got {hc.get('Timeout')}"
    )
    assert hc.get("Retries") == 3, (
        f"Expected Retries=3, got {hc.get('Retries')}"
    )


# ===========================================================================
# T-08: Runtime UID is 1000
# ===========================================================================


@pytest.mark.real
def test_t08_runtime_uid_is_1000(built_mcp_image):
    """T-08: Container runs as UID 1000 (appuser).

    feature-44
    Traces: §Algorithm Boundary: UID selection
    Kills bug: useradd skipped or wrong UID used.
    """
    result = subprocess.run(
        ["docker", "run", "--rm", built_mcp_image, "id", "-u"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"id -u failed: {result.stderr}"
    assert result.stdout.strip() == "1000", (
        f"Expected UID 1000, got: {result.stdout.strip()!r}"
    )


# ===========================================================================
# T-09: pytest is not installed (error path)
# ===========================================================================


@pytest.mark.real
def test_t09_pytest_not_installed(built_mcp_image):
    """T-09: 'pip show pytest' exits non-zero — pytest is not present in image.

    feature-44
    Traces: §Algorithm Error Handling: dev packages
    Kills bug: Dev extras accidentally installed via pip install .[dev].
    """
    result = subprocess.run(
        ["docker", "run", "--rm", built_mcp_image, "pip", "show", "pytest"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"'pip show pytest' succeeded — pytest should NOT be in the image.\n"
        f"Output: {result.stdout}"
    )


# ===========================================================================
# T-10: EXPOSE 3000 is declared (streamable-http port)
# ===========================================================================


@pytest.mark.real
def test_t10_exposes_port_3000(built_mcp_image):
    """T-10: Image declares EXPOSE 3000 to match MCP_PORT default.

    feature-44
    Traces: §Algorithm Boundary: EXPOSE matches MCP_PORT
    Kills bug: EXPOSE missing or wrong port — clients in same docker network
    cannot discover the streamable-http listener.
    """
    info = docker_inspect(built_mcp_image)
    exposed = info["Config"].get("ExposedPorts") or {}
    assert "3000/tcp" in exposed, (
        f"Expected EXPOSE 3000/tcp for streamable-http MCP server, got: {exposed}"
    )


# ===========================================================================
# T-11: HEALTHCHECK detects process crash → container becomes unhealthy
# ===========================================================================


@pytest.mark.real
def test_t11_healthcheck_detects_crash(built_mcp_image):
    """T-11: Container becomes unhealthy when streamable-http listener is absent.

    Runs image with an entrypoint override (sleep) so that mcp_server never
    starts and port 3000 stays unbound — socket.create_connection fails →
    healthcheck returns non-zero. Uses fast health-check overrides (2s
    interval, 1s timeout, 2 retries) so the test completes in ~10 seconds
    instead of 90s.

    feature-44
    Traces: §Algorithm Error Handling: listener-down check
    Kills bug: HEALTHCHECK command wrong (never detects unbound port).
    """
    container_name = "codecontext-mcp-test-healthcheck"
    # Clean up any lingering container from previous run
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
    )

    # Run with sleep entrypoint — mcp_server never starts, so pgrep returns non-zero
    run_result = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            container_name,
            "--health-interval=2s",
            "--health-timeout=1s",
            "--health-retries=2",
            "--entrypoint",
            "sleep",
            built_mcp_image,
            "60",
        ],
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, (
        f"Failed to start container: {run_result.stderr}"
    )

    try:
        # Wait long enough for 2 retries at 2s interval: ~6–8 seconds
        time.sleep(10)

        inspect_result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
            check=True,
        )
        container_info = json.loads(inspect_result.stdout)[0]
        health_status = container_info["State"]["Health"]["Status"]
        assert health_status == "unhealthy", (
            f"Expected container to be unhealthy when mcp_server not running, "
            f"got status: {health_status!r}"
        )
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


# ===========================================================================
# T-12: CMD is exec-form (JSON array), not shell-form string
# ===========================================================================


@pytest.mark.real
def test_t12_cmd_is_exec_form_array(built_mcp_image):
    """T-12: CMD is a JSON array (exec-form), NOT a shell string.

    feature-44
    Traces: §Algorithm Boundary: exec-form CMD
    Kills bug: Shell-form CMD wraps in /bin/sh -c, making python NOT PID 1.
    """
    info = docker_inspect(built_mcp_image)
    cmd = info["Config"]["Cmd"]
    # Exec-form: list of strings, e.g. ["python", "-m", "src.query.mcp_server"]
    # Shell-form: ["/bin/sh", "-c", "python -m src.query.mcp_server"]
    assert isinstance(cmd, list), f"Expected CMD to be a list, got: {type(cmd)}"
    assert len(cmd) == 3, f"Expected 3 elements in exec-form CMD, got: {cmd}"
    assert cmd[0] == "python", f"Expected CMD[0]='python', got: {cmd[0]!r}"
    assert cmd[1] == "-m", f"Expected CMD[1]='-m', got: {cmd[1]!r}"
    assert cmd[2] == "src.query.mcp_server", (
        f"Expected CMD[2]='src.query.mcp_server', got: {cmd[2]!r}"
    )
    # Verify it's NOT shell-form (no /bin/sh wrapper)
    assert "/bin/sh" not in cmd, (
        f"CMD appears to be shell-form (contains /bin/sh): {cmd}"
    )


# ===========================================================================
# T-13: Container stays running detached (no -i) — regression gate for the
#       silent-stdio-exit bug
# ===========================================================================


@pytest.mark.real
def test_t13_container_stays_running_detached(built_mcp_image):
    """T-13: ``docker run -d`` (no ``-i``) keeps the container alive.

    Hard regression gate: prior to 2026-05-06 the image used stdio transport
    and exited within ~1 s when stdin was closed. With streamable-http the
    container must remain running and pass health checks. Uses a fast
    health-check override (2s interval, 1s timeout, 2 retries) so the assert
    fires within ~10 s instead of 90 s.

    feature-44
    Traces: VS-2 (rewritten) — container stays running detached
    Kills bug: Reverting mcp.run() to stdio.
    """
    container_name = "codecontext-mcp-test-detached"
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    run_result = subprocess.run(
        [
            "docker", "run", "--detach",
            "--name", container_name,
            "--health-interval=2s",
            "--health-timeout=1s",
            "--health-retries=2",
            "-e", "DATABASE_URL=postgresql+asyncpg://x:x@127.0.0.1/db",
            "-e", "ELASTICSEARCH_URL=http://127.0.0.1:9200",
            "-e", "QDRANT_URL=http://127.0.0.1:6333",
            built_mcp_image,
        ],
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, (
        f"Failed to start container detached: {run_result.stderr}"
    )

    try:
        # Allow time for the streamable-http listener + first health probe
        time.sleep(8)
        inspect_result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True, text=True, check=True,
        )
        info = json.loads(inspect_result.stdout)[0]
        state = info["State"]
        assert state["Status"] == "running", (
            f"Container exited unexpectedly. Status={state['Status']}, "
            f"ExitCode={state.get('ExitCode')}, "
            f"Logs:\n{_container_logs(container_name)}"
        )
        health = state.get("Health", {}).get("Status")
        assert health in ("healthy", "starting"), (
            f"Container health is {health!r} (expected healthy/starting). "
            f"Logs:\n{_container_logs(container_name)}"
        )
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


def _container_logs(name: str) -> str:
    r = subprocess.run(
        ["docker", "logs", "--tail", "40", name],
        capture_output=True, text=True,
    )
    return (r.stdout or "") + (r.stderr or "")


# ===========================================================================
# T-14: git binary is installed (required by GitCloner.list_remote_branches
#       used to populate available_branches)
# ===========================================================================


@pytest.mark.real
def test_t14_git_available_in_image(built_mcp_image):
    """T-14: ``git --version`` succeeds inside the image.

    feature-44
    Traces: VS-4 (rewritten) — git in production deps
    Kills bug: ``apt-get install git`` removed → available_branches always
    silently empty (FileNotFoundError swallowed by ``except Exception``).
    """
    result = subprocess.run(
        ["docker", "run", "--rm", built_mcp_image, "git", "--version"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"git not available in image: rc={result.returncode}, "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert "git version" in result.stdout, (
        f"Unexpected git --version output: {result.stdout!r}"
    )


# ===========================================================================
# T-15: End-to-end MCP initialize JSON-RPC handshake over streamable-http
# ===========================================================================


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


@pytest.mark.real
def test_t15_mcp_initialize_handshake(built_mcp_image):
    """T-15: POST /mcp initialize returns serverInfo.name=code-context-retrieval.

    Genuine end-to-end test: starts the container with port 3000 published,
    waits for the listener, then performs a real MCP JSON-RPC handshake via
    HTTP. This is the strongest evidence that the container is usable, not
    just structurally correct.

    feature-44
    Traces: VS-5 (new) — runtime MCP handshake works
    Kills bug: Wrong transport / wrong path / handler import failure.
    """
    import http.client

    container_name = "codecontext-mcp-test-e2e"
    host_port = "33700"  # avoid conflict with any local 3000
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    run_result = subprocess.run(
        [
            "docker", "run", "--detach",
            "--name", container_name,
            "-p", f"{host_port}:3000",
            "-e", "DATABASE_URL=postgresql+asyncpg://x:x@127.0.0.1/db",
            "-e", "ELASTICSEARCH_URL=http://127.0.0.1:9200",
            "-e", "QDRANT_URL=http://127.0.0.1:6333",
            built_mcp_image,
        ],
        capture_output=True, text=True,
    )
    assert run_result.returncode == 0, (
        f"Failed to start container: {run_result.stderr}"
    )

    try:
        assert _wait_for_port(int(host_port), timeout=20.0), (
            f"streamable-http listener never came up on :{host_port}\n"
            f"Logs:\n{_container_logs(container_name)}"
        )

        body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "feature-44-test", "version": "0.0.0"},
            },
        })
        # The TCP listener accepts connections slightly before the
        # StreamableHTTP session manager is ready; the first POST can RST.
        # Retry up to 3 times with short backoff before failing.
        last_err: Exception | None = None
        resp = None
        raw = ""
        for attempt in range(3):
            conn = http.client.HTTPConnection(
                "127.0.0.1", int(host_port), timeout=10,
            )
            try:
                conn.request(
                    "POST", "/mcp", body=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                    },
                )
                resp = conn.getresponse()
                raw = resp.read().decode("utf-8", errors="replace")
                break
            except (ConnectionResetError, http.client.RemoteDisconnected) as exc:
                last_err = exc
                time.sleep(1.0 + attempt)
            finally:
                conn.close()
        assert resp is not None, (
            f"All 3 POST /mcp attempts reset. last_err={last_err!r}\n"
            f"Logs:\n{_container_logs(container_name)}"
        )

        assert resp.status == 200, (
            f"Expected 200 from /mcp initialize, got {resp.status}.\n"
            f"Body: {raw[:500]}\nLogs:\n{_container_logs(container_name)}"
        )
        # streamable-http may return JSON or SSE-framed event(s); both
        # contain the JSON-RPC payload.
        assert "code-context-retrieval" in raw, (
            f"serverInfo.name not in response. Body: {raw[:500]}"
        )
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
