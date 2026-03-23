"""Tests for Feature #45 — index-worker Docker Image (docker/Dockerfile.worker).

SRS: FR-029: index-worker Docker Image [Wave 4]

All tests are Docker integration tests and require a running Docker daemon.
They are marked @pytest.mark.real and use a session-scoped fixture that builds
the image once and tears it down after all tests complete.

Test layers:
  [integration] — Docker daemon required; builds and inspects codecontext-worker-test image

Security: N/A — Dockerfile is a declarative build spec with no user-facing input surface.
"""

# [mutation-exempt] — Dockerfile-only feature (docker/Dockerfile.worker); zero Python src/ code added.
# Mutation testing (mutmut) is N/A: no Python source to mutate. All test assertions verify
# Docker behavior via subprocess; mutmut sandbox (mutants/) cannot run Docker integration tests.

from __future__ import annotations

import json
import subprocess

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMAGE_TAG = "codecontext-worker-test"
DOCKERFILE_PATH = "docker/Dockerfile.worker"


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
def built_worker_image():
    """Build docker/Dockerfile.worker once for the session; remove image on teardown.

    feature-45
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
    """T-01: docker build with Dockerfile.worker exits 0 and produces the image.

    feature-45
    Traces: VS-1, FR-029 AC-1
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
    ls_result = subprocess.run(
        ["docker", "image", "inspect", IMAGE_TAG],
        capture_output=True,
        text=True,
    )
    assert ls_result.returncode == 0, "Image not found in local registry after build"


# ===========================================================================
# T-02: CMD is exec-form ["celery", "-A", "src.indexing.celery_app", "worker", "--loglevel=info"]
# ===========================================================================


@pytest.mark.real
def test_t02_cmd_is_celery_worker(built_worker_image):
    """T-02: Image CMD equals the full celery worker exec-form array.

    feature-45
    Traces: VS-2, FR-029 AC-2
    Kills bug: Wrong CMD (shell-form, wrong module path, missing --loglevel, etc.)
    """
    info = docker_inspect(built_worker_image)
    cmd = info["Config"]["Cmd"]
    expected = ["celery", "-A", "src.indexing.celery_app", "worker", "--loglevel=info"]
    assert cmd == expected, (
        f"Expected CMD {expected}, got: {cmd}"
    )


# ===========================================================================
# T-03: HEALTHCHECK contains celery inspect ping src.indexing.celery_app
# ===========================================================================


@pytest.mark.real
def test_t03_healthcheck_uses_celery_inspect_ping(built_worker_image):
    """T-03: Image HEALTHCHECK contains 'celery', 'inspect ping', and 'src.indexing.celery_app'.

    feature-45
    Traces: VS-3, FR-029 AC-3
    Kills bug: Missing HEALTHCHECK or wrong command (e.g., pgrep copied from MCP image).
    """
    info = docker_inspect(built_worker_image)
    healthcheck = info["Config"].get("Healthcheck", {})
    assert healthcheck, "No HEALTHCHECK defined in image config"
    test_cmd = healthcheck.get("Test", [])
    assert test_cmd, "HEALTHCHECK.Test is empty"
    full_cmd = " ".join(test_cmd)
    assert "celery" in full_cmd, f"HEALTHCHECK does not use celery: {test_cmd}"
    assert "inspect" in full_cmd, f"HEALTHCHECK does not contain 'inspect': {test_cmd}"
    assert "ping" in full_cmd, f"HEALTHCHECK does not contain 'ping': {test_cmd}"
    assert "src.indexing.celery_app" in full_cmd, (
        f"HEALTHCHECK does not reference src.indexing.celery_app: {test_cmd}"
    )


# ===========================================================================
# T-04: Dev packages (pytest, mutmut, locust) NOT installed
# ===========================================================================


@pytest.mark.real
def test_t04_no_dev_packages_installed(built_worker_image):
    """T-04: Image does not contain dev packages (pytest, mutmut, locust).

    feature-45
    Traces: VS-4, FR-029 AC-4
    Kills bug: Accidental pip install .[dev] in Dockerfile.
    """
    result = subprocess.run(
        ["docker", "run", "--rm", built_worker_image, "pip", "list"],
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
def test_t05_runtime_user_is_appuser(built_worker_image):
    """T-05: Image Config.User is 'appuser' or '1000' (non-root).

    feature-45
    Traces: VS-4, FR-029 AC-4
    Kills bug: Missing USER appuser instruction.
    """
    info = docker_inspect(built_worker_image)
    user = info["Config"].get("User", "")
    assert user in ("appuser", "1000"), (
        f"Expected User=appuser or 1000, got: '{user}'"
    )


# ===========================================================================
# T-06: Build fails when Dockerfile.worker is absent
# ===========================================================================


@pytest.mark.real
def test_t06_build_fails_without_dockerfile(tmp_path):
    """T-06: docker build exits non-zero when Dockerfile.worker does not exist.

    feature-45
    Traces: §Algorithm Error Handling: Dockerfile.worker absent
    Kills bug: Test passes even when Dockerfile is missing (wrong setup).
    """
    result = subprocess.run(
        [
            "docker",
            "build",
            "-f",
            str(tmp_path / "Dockerfile.nonexistent"),
            "-t",
            "codecontext-worker-test-shouldfail",
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
# T-07: HEALTHCHECK interval=60s, timeout=30s, retries=3
# ===========================================================================


@pytest.mark.real
def test_t07_healthcheck_timing_values(built_worker_image):
    """T-07: HEALTHCHECK interval=60s (60e9 ns), timeout=30s (30e9 ns), retries=3.

    feature-45
    Traces: §Algorithm Boundary: HEALTHCHECK interval/timeout
    Kills bug: Wrong timing values (e.g., 30s/5s copied from MCP image).
    """
    info = docker_inspect(built_worker_image)
    hc = info["Config"].get("Healthcheck", {})
    assert hc, "No HEALTHCHECK defined"
    assert hc.get("Interval") == 60_000_000_000, (
        f"Expected Interval=60000000000 ns (60s), got {hc.get('Interval')}"
    )
    assert hc.get("Timeout") == 30_000_000_000, (
        f"Expected Timeout=30000000000 ns (30s), got {hc.get('Timeout')}"
    )
    assert hc.get("Retries") == 3, (
        f"Expected Retries=3, got {hc.get('Retries')}"
    )


# ===========================================================================
# T-08: Runtime UID is 1000
# ===========================================================================


@pytest.mark.real
def test_t08_runtime_uid_is_1000(built_worker_image):
    """T-08: Container runs as UID 1000 (appuser).

    feature-45
    Traces: §Algorithm Boundary: UID selection
    Kills bug: useradd skipped or wrong UID used.
    """
    result = subprocess.run(
        ["docker", "run", "--rm", built_worker_image, "id", "-u"],
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
def test_t09_pytest_not_installed(built_worker_image):
    """T-09: 'pip show pytest' exits non-zero — pytest is not present in image.

    feature-45
    Traces: §Algorithm Error Handling: dev packages
    Kills bug: Dev extras accidentally installed via pip install .[dev].
    """
    result = subprocess.run(
        ["docker", "run", "--rm", built_worker_image, "pip", "show", "pytest"],
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
def test_t10_no_exposed_ports(built_worker_image):
    """T-10: Image has no EXPOSE instruction (ExposedPorts is null or empty).

    feature-45
    Traces: §Algorithm Boundary: no EXPOSE
    Kills bug: Spurious EXPOSE instruction added (Celery workers use broker, not inbound ports).
    """
    info = docker_inspect(built_worker_image)
    exposed = info["Config"].get("ExposedPorts")
    assert not exposed, (
        f"Expected no exposed ports for Celery worker, got: {exposed}"
    )


# ===========================================================================
# T-11: CMD is exec-form (JSON array), not shell-form string
# ===========================================================================


@pytest.mark.real
def test_t11_cmd_is_exec_form_array(built_worker_image):
    """T-11: CMD is a JSON array (exec-form), NOT a shell string.

    feature-45
    Traces: §Algorithm Boundary: exec-form CMD
    Kills bug: Shell-form CMD wraps in /bin/sh -c, making celery NOT PID 1.
    """
    info = docker_inspect(built_worker_image)
    cmd = info["Config"]["Cmd"]
    assert isinstance(cmd, list), f"Expected CMD to be a list, got: {type(cmd)}"
    assert cmd[0] == "celery", f"Expected CMD[0]='celery', got: {cmd[0]!r}"
    assert "/bin/sh" not in cmd, (
        f"CMD appears to be shell-form (contains /bin/sh): {cmd}"
    )


# ===========================================================================
# T-12: HEALTHCHECK targets local worker with -d celery@$HOSTNAME
# ===========================================================================


@pytest.mark.real
def test_t12_healthcheck_targets_local_worker(built_worker_image):
    """T-12: HEALTHCHECK contains '-d celery@$HOSTNAME' to target only the local container.

    feature-45
    Traces: §Algorithm Boundary: HEALTHCHECK targets local worker
    Kills bug: Missing -d flag (would ping all workers in cluster instead of local one).
    """
    info = docker_inspect(built_worker_image)
    hc = info["Config"].get("Healthcheck", {})
    test_cmd = hc.get("Test", [])
    full_cmd = " ".join(test_cmd)
    assert "-d" in full_cmd, (
        f"HEALTHCHECK missing '-d' flag for worker targeting: {test_cmd}"
    )
    assert "celery@$HOSTNAME" in full_cmd, (
        f"HEALTHCHECK does not target 'celery@$HOSTNAME': {test_cmd}"
    )


# ===========================================================================
# T-13: celery CLI is installed (production dep)
# ===========================================================================


@pytest.mark.real
def test_t13_celery_cli_is_installed(built_worker_image):
    """T-13: 'celery --version' exits 0 — celery is installed as a production dep.

    feature-45
    Traces: §Algorithm Error Handling: celery CLI available
    Kills bug: celery not installed (HEALTHCHECK 'celery inspect ping' would always fail).
    """
    result = subprocess.run(
        ["docker", "run", "--rm", built_worker_image, "celery", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"'celery --version' failed — celery must be installed in the image.\n"
        f"STDERR: {result.stderr}"
    )
    output = result.stdout.strip()
    assert output, "celery --version produced no output"
    # Version string should contain a digit (e.g., "5.3.6")
    assert any(c.isdigit() for c in output), (
        f"celery --version output doesn't look like a version: {output!r}"
    )


# ===========================================================================
# T-14: --loglevel=info is present in CMD
# ===========================================================================


@pytest.mark.real
def test_t14_loglevel_info_in_cmd(built_worker_image):
    """T-14: CMD array contains '--loglevel=info' element.

    feature-45
    Traces: §Algorithm Boundary: loglevel flag
    Kills bug: Missing --loglevel flag (silent worker, hard to debug startup/task events).
    """
    info = docker_inspect(built_worker_image)
    cmd = info["Config"]["Cmd"]
    assert "--loglevel=info" in cmd, (
        f"Expected '--loglevel=info' in CMD array, got: {cmd}"
    )
