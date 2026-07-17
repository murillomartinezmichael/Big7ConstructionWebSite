#!/usr/bin/env python3
"""Build and smoke-test the production nginx container.

This is intentionally separate from the stdlib-only static contract suite:
it requires a running Docker daemon and proves the image can boot as the
configured non-root user after the runtime PORT substitution.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTAINER_PORT = 8080
ROUTES = (
    ("/", 200),
    ("/commercial-industrial.html", 200),
    ("/residential-construction.html", 200),
    ("/home-repair.html", 200),
    ("/__big7_container_smoke_missing__", 404),
)
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class SmokeFailure(RuntimeError):
    """Expected smoke-test failure with a human-readable message."""


def _command_text(args: list[str]) -> str:
    return " ".join(args)


def _capture(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SmokeFailure(
            f"command failed ({result.returncode}): {_command_text(args)}"
            + (f"\n{detail}" if detail else "")
        )
    return result


def _stream(args: list[str]) -> None:
    print(f"$ {_command_text(args)}", flush=True)
    result = subprocess.run(args, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise SmokeFailure(
            f"command failed ({result.returncode}): {_command_text(args)}"
        )


def _inspect(container_name: str) -> dict[str, Any]:
    result = _capture(["docker", "inspect", container_name])
    try:
        documents = json.loads(result.stdout)
        return documents[0]
    except (json.JSONDecodeError, IndexError, TypeError) as exc:
        raise SmokeFailure(f"could not parse docker inspect output: {exc}") from exc


def _container_state(container_name: str) -> dict[str, Any]:
    return _inspect(container_name).get("State", {})


def _early_exit_message(container_name: str, state: dict[str, Any]) -> str:
    status = state.get("Status", "unknown")
    exit_code = state.get("ExitCode", "unknown")
    error = state.get("Error") or "none"
    return (
        f"container exited before becoming ready "
        f"(status={status}, exit_code={exit_code}, error={error})"
    )


def _wait_for_host_port(container_name: str, deadline: float) -> int:
    while time.monotonic() < deadline:
        document = _inspect(container_name)
        state = document.get("State", {})
        if not state.get("Running", False):
            raise SmokeFailure(_early_exit_message(container_name, state))

        ports = document.get("NetworkSettings", {}).get("Ports", {})
        bindings = ports.get(f"{CONTAINER_PORT}/tcp") or []
        if bindings and bindings[0].get("HostPort"):
            return int(bindings[0]["HostPort"])
        time.sleep(0.2)

    raise SmokeFailure("Docker did not publish the container port before timeout")


def _request(base_url: str, path: str) -> tuple[int, bytes]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        headers={"User-Agent": "big7-container-smoke/1.0"},
    )
    try:
        with HTTP.open(request, timeout=3) as response:
            return response.status, response.read(250_000)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(250_000)


def _wait_until_ready(container_name: str, base_url: str, deadline: float) -> None:
    last_error = "no HTTP response"
    while time.monotonic() < deadline:
        state = _container_state(container_name)
        if not state.get("Running", False):
            raise SmokeFailure(_early_exit_message(container_name, state))

        try:
            status, _ = _request(base_url, "/")
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(0.25)
            continue

        if status == 200:
            return
        raise SmokeFailure(f"readiness route returned HTTP {status}, expected 200")

    raise SmokeFailure(f"container did not become HTTP-ready before timeout ({last_error})")


def _assert_routes(base_url: str) -> None:
    for path, expected in ROUTES:
        try:
            actual, body = _request(base_url, path)
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise SmokeFailure(f"GET {path} failed: {type(exc).__name__}: {exc}") from exc

        if actual != expected:
            raise SmokeFailure(f"GET {path} returned HTTP {actual}, expected {expected}")
        if path == "/" and b"Big 7 Construction" not in body:
            raise SmokeFailure("GET / returned 200 but the Big 7 brand signature was absent")
        print(f"  OK  GET {path} -> {actual}")


def _logs(container_name: str) -> str:
    result = _capture(["docker", "logs", container_name], check=False)
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return output or "(no container logs emitted)"


def _cleanup(container_name: str, image_tag: str, *, container_created: bool, image_built: bool) -> None:
    print("Cleaning up Docker smoke resources...")
    if container_created:
        result = _capture(["docker", "rm", "--force", container_name], check=False)
        if result.returncode != 0 and "No such container" not in result.stderr:
            print(f"WARN: could not remove container: {result.stderr.strip()}", file=sys.stderr)
    if image_built:
        result = _capture(["docker", "image", "rm", "--force", image_tag], check=False)
        if result.returncode != 0 and "No such image" not in result.stderr:
            print(f"WARN: could not remove image: {result.stderr.strip()}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="seconds to wait for Docker port publication and HTTP readiness (default: 45)",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    if shutil.which("docker") is None:
        print("FAIL: docker CLI is not installed or not on PATH", file=sys.stderr)
        return 1

    suffix = f"{os.getpid()}-{uuid.uuid4().hex[:8]}".lower()
    image_tag = f"big7-container-smoke:{suffix}"
    container_name = f"big7-container-smoke-{suffix}"
    image_built = False
    container_created = False

    try:
        server_version = _capture(
            ["docker", "version", "--format", "{{.Server.Version}}"]
        ).stdout.strip()
        if not server_version:
            raise SmokeFailure("Docker daemon did not report a server version")
        print(f"Docker server: {server_version}")

        _stream(["docker", "build", "--tag", image_tag, "."])
        image_built = True

        result = _capture(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                container_name,
                "--env",
                f"PORT={CONTAINER_PORT}",
                "--publish",
                f"127.0.0.1::{CONTAINER_PORT}",
                image_tag,
            ]
        )
        container_created = True
        print(f"Container: {result.stdout.strip()[:12]}")

        deadline = time.monotonic() + args.timeout
        host_port = _wait_for_host_port(container_name, deadline)
        base_url = f"http://127.0.0.1:{host_port}"
        _wait_until_ready(container_name, base_url, deadline)
        _assert_routes(base_url)
        print("PASS: production container booted and all route contracts held")
        return 0
    except KeyboardInterrupt:
        print("FAIL: interrupted", file=sys.stderr)
        return 130
    except (SmokeFailure, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        if container_created:
            print("--- container logs ---", file=sys.stderr)
            print(_logs(container_name), file=sys.stderr)
            print("--- end container logs ---", file=sys.stderr)
        return 1
    finally:
        _cleanup(
            container_name,
            image_tag,
            container_created=container_created,
            image_built=image_built,
        )


if __name__ == "__main__":
    raise SystemExit(main())
