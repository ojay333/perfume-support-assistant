r"""Run only the allowlisted offline checks in isolated Python processes.

Usage from the release root:
    .venv\Scripts\python.exe scripts/run_tests.py --smoke-repeat 2

No real API keys or .env files are used. The optional smoke check owns a new
loopback-only server on an ephemeral port and stops only that server.
The Python audit guard is protection against accidental I/O, not a sandbox for
running untrusted Python code.
"""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import platform
import runpy
import socket
import subprocess
import sys
import threading
import time
import traceback
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "customer_support_agent"
TESTS = (
    "test_draft_schema.py",
    "test_followup.py",
    "test_ticket_client.py",
    "test_followup_workflow.py",
    "test_llm_client.py",
    "test_policy_reader.py",
    "test_retrieval.py",
    "test_rag_client.py",
    "test_api.py",
)
FAKE_KEY = "offline-test-only-not-a-real-api-key"


def clean_environment():
    """Carry only Windows/runtime basics; never inherit credentials or proxies."""
    allowed = {
        "systemroot", "windir", "comspec", "path", "pathext", "temp", "tmp",
        "systemdrive", "lang", "lc_all",
    }
    result = {key: value for key, value in os.environ.items() if key.lower() in allowed}
    result.update({
        "GOOGLE_API_KEY": FAKE_KEY,
        "GEMINI_API_KEY": FAKE_KEY,
        "PYTHON_DOTENV_DISABLED": "1",
    })
    return result


class OfflineViolation(RuntimeError):
    pass


def install_guard():
    """Block external sockets, secret/holdout reads, and child-process escapes."""
    violations = []

    def reject(reason):
        violations.append(reason)
        raise OfflineViolation(reason)

    def loopback(host):
        if isinstance(host, bytes):
            host = host.decode("ascii", errors="replace")
        if host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except (ValueError, TypeError):
            return False

    def audit(event, args):
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            name = Path(os.fsdecode(args[0])).name.lower()
            if name == ".env" or name.startswith(".env."):
                reject("Offline checks must not open .env files.")
            if name == "eval_cases.json":
                reject("Offline checks must not open evaluation/holdout cases.")
        elif event in {"socket.connect", "socket.bind", "socket.sendto"}:
            address = args[1]
            if not isinstance(address, tuple) or not loopback(address[0]):
                reject("External or non-loopback socket access is blocked.")
        elif event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}:
            if not loopback(args[0]):
                reject("External DNS lookup is blocked.")
        elif event == "socket.getnameinfo":
            if not loopback(args[0][0]):
                reject("External reverse DNS lookup is blocked.")
        elif event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}:
            reject("Offline test workers must not launch other processes.")

    sys.addaudithook(audit)
    return violations


def smoke_check():
    """Use real local HTTP, without keys or model requests, in this fresh worker."""
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    import uvicorn
    from api import app

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=port, loop="asyncio", lifespan="off",
        log_level="warning", access_log=False,
    ))
    failures = []

    def serve():
        try:
            server.run(sockets=[listener])
        except BaseException as error:
            failures.append(error)

    worker = threading.Thread(target=serve, name="owned-offline-smoke", daemon=True)
    worker.start()
    opener = build_opener(ProxyHandler({}))

    def request(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(
            f"http://127.0.0.1:{port}{path}", data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            response = opener.open(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read().decode("utf-8"))

    try:
        deadline = time.monotonic() + 10
        while not server.started and worker.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        if failures:
            raise RuntimeError("The owned smoke server failed to start.") from failures[0]
        if not server.started:
            raise RuntimeError("The owned smoke server did not start in time.")

        assert request("/health") == (200, {"status": "ok"})
        for endpoint in ("/ask", "/requests"):
            status, _ = request(endpoint, {"user_input": "   "})
            assert status == 422, (endpoint, status)
            status, body = request(endpoint, {"user_input": "سؤال محلي تجريبي"})
            assert status == 500, (endpoint, status)
            assert body == {"detail": "مفتاح Gemini غير متاح"}, (endpoint, body)
        print("Smoke: health 200; both routes blank 422 and missing-key 500.")
    finally:
        server.should_exit = True
        worker.join(timeout=5)
        listener.close()
        if worker.is_alive():
            raise RuntimeError("The owned smoke server did not stop in time.")
    if failures:
        raise RuntimeError("The owned smoke server failed.") from failures[0]


def run_child(name):
    if name not in TESTS and name != "smoke":
        raise ValueError("Test is not allowlisted.")
    environment = clean_environment()
    os.environ.clear()
    os.environ.update(environment)
    os.chdir(ROOT)
    sys.path.insert(0, str(APP))
    sys.dont_write_bytecode = True
    # Windows' stdlib platform detection may invoke `ver` once. Warm that
    # trusted cache before enabling the no-subprocess rule for app/test code.
    platform.system()
    violations = install_guard()

    # Patch before importing any app/test module, including older dotenv versions.
    import dotenv
    import dotenv.main
    dotenv.load_dotenv = lambda *args, **kwargs: False
    dotenv.main.load_dotenv = dotenv.load_dotenv

    status = 0
    try:
        if name == "smoke":
            smoke_check()
        else:
            target = APP / name
            sys.argv = [str(target)]
            runpy.run_path(str(target), run_name="__main__")
    except SystemExit as error:
        status = 0 if error.code is None else error.code
        if not isinstance(status, int):
            print(status, file=sys.stderr)
            status = 1
    except BaseException:
        traceback.print_exc()
        status = 1
    if violations:
        print("Offline guard violation(s): " + "; ".join(violations), file=sys.stderr)
        status = 1
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="also check an owned local HTTP server")
    parser.add_argument(
        "--smoke-repeat", type=int, choices=(1, 2), default=0,
        help="run smoke in 1 or 2 fresh processes; 2 also checks clean stop/restart",
    )
    parser.add_argument("--_child", choices=(*TESTS, "smoke"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not __debug__:
        parser.error("Assertions must be enabled; do not use Python -O or -OO.")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if args._child:
        return run_child(args._child)

    smoke_runs = args.smoke_repeat or int(args.smoke)
    jobs = TESTS + ("smoke",) * smoke_runs
    failures = 0
    for job_index, name in enumerate(jobs):
        label = name if name != "smoke" else f"smoke {job_index - len(TESTS) + 1}/{smoke_runs}"
        command = [
            sys.executable, "-I", "-B", "-X", "utf8", "-u",
            str(Path(__file__).resolve()), "--_child", name,
        ]
        try:
            result = subprocess.run(
                command, cwd=ROOT, env=clean_environment(), capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=60,
            )
        except subprocess.TimeoutExpired:
            print(f"FAIL {label}: exceeded 60 seconds; only its worker was stopped.")
            failures += 1
            continue
        if result.returncode:
            failures += 1
            print(f"FAIL {label} (exit {result.returncode})")
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip(), file=sys.stderr)
        else:
            print(f"PASS {label}")
            if name == "smoke" and result.stdout:
                print(result.stdout.rstrip())
    print(f"{len(jobs) - failures}/{len(jobs)} checks passed; no live Gemini evaluation was run.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
