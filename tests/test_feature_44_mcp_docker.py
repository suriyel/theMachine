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

from __future__ import annotations

import json
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
# T-03: HEALTHCHECK contains pgrep -f "src.query.mcp_server"
# ===========================================================================


@pytest.mark.real
def test_t03_healthcheck_uses_pgrep(built_mcp_image):
    """T-03: Image HEALTHCHECK.Test contains 'pgrep -f' and 'src.query.mcp_server'.

    feature-44
    Traces: VS-3, FR-028 AC-3
    Kills bug: Missing HEALTHCHECK instruction.
    """
    info = docker_inspect(built_mcp_image)
    healthcheck = info["Config"].get("Healthcheck", {})
    assert healthcheck, "No HEALTHCHECK defined in image config"
    test_cmd = healthcheck.get("Test", [])
    assert test_cmd, "HEALTHCHECK.Test is empty"
    # Test field is e.g. ["CMD", "pgrep -f \"src.query.mcp_server\" || exit 1"]
    full_cmd = " ".join(test_cmd)
    assert "pgrep" in full_cmd, f"HEALTHCHECK does not use pgrep: {test_cmd}"
    assert "src.query.mcp_server" in full_cmd, (
        f"HEALTHCHECK does not reference src.query.mcp_server: {test_cmd}"
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
# T-10: No EXPOSE instruction
# ===========================================================================


@pytest.mark.real
def test_t10_no_exposed_ports(built_mcp_image):
    """T-10: Image has no EXPOSE instruction (ExposedPorts is null or empty).

    feature-44
    Traces: §Algorithm Boundary: no EXPOSE
    Kills bug: Spurious EXPOSE instruction added (MCP is stdio-only, no port needed).
    """
    info = docker_inspect(built_mcp_image)
    exposed = info["Config"].get("ExposedPorts")
    assert not exposed, (
        f"Expected no exposed ports for stdio MCP server, got: {exposed}"
    )


# ===========================================================================
# T-11: HEALTHCHECK detects process crash → container becomes unhealthy
# ===========================================================================


@pytest.mark.real
def test_t11_healthcheck_detects_crash(built_mcp_image):
    """T-11: Container becomes unhealthy when mcp_server process is not running.

    Runs image with an entrypoint override (sleep) so that pgrep -f src.query.mcp_server
    finds no process. Uses fast health-check overrides (2s interval, 1s timeout, 2 retries)
    so the test completes in ~10 seconds instead of 90s.

    feature-44
    Traces: §Algorithm Error Handling: process alive check
    Kills bug: HEALTHCHECK command wrong (never detects crash).
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
