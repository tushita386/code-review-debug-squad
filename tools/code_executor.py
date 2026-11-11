"""Restricted Python test execution.

Isolation: separate subprocess (never the Streamlit process), isolated mode (-I), temp working directory,
scrubbed environment (no API keys), wall-clock timeout, per-test alarm + CPU/memory/file-size limits on
Linux/macOS, and a guard that blocks user code from importing os/subprocess/socket/etc.
LIMITATIONS: this is NOT a full sandbox (no container/VM). On Windows memory/CPU limits are unavailable and
network blocking relies on the import guard. Use only for student-sized programs.
"""
import json
import os
import subprocess
import sys
import tempfile

RUNNER = r'''
import builtins, io, json, sys
BLOCKED = {"os", "subprocess", "socket", "shutil", "ctypes", "multiprocessing", "requests", "urllib",
           "http", "ftplib", "smtplib", "telnetlib", "pathlib", "importlib", "sys", "signal", "threading"}
real_import = builtins.__import__
def guard(name, globals=None, locals=None, fromlist=(), level=0):
    if (globals is None or globals.get("__name__") == "user_code") and name.split(".")[0] in BLOCKED:
        raise ImportError("import of '%s' is blocked in the sandbox" % name)
    return real_import(name, globals, locals, fromlist, level)

code = open("code.py", encoding="utf-8").read()
tests = json.load(open("tests.json", encoding="utf-8"))
results = []
def finish():
    json.dump(results, open("results.json", "w", encoding="utf-8"))

try:
    import signal
    HAS_ALARM = hasattr(signal, "SIGALRM")
except Exception:
    HAS_ALARM = False

class Timeout(Exception):
    pass
def _on_alarm(*a):
    raise Timeout()
if HAS_ALARM:
    signal.signal(signal.SIGALRM, _on_alarm)

ns = {"__name__": "user_code"}
builtins.__import__ = guard
real_stdout = sys.stdout
sys.stdout = io.StringIO()
load_error = None
try:
    exec(compile(code, "code.py", "exec"), ns)
except BaseException as e:
    load_error = "%s: %s" % (type(e).__name__, e)

for t in tests:
    r = {"name": t["name"], "status": "ERROR", "actual": "", "error": ""}
    if load_error:
        r["error"] = "Code failed to load: " + load_error
    else:
        try:
            if HAS_ALARM:
                signal.alarm(2)
            actual = eval(t["call_expression"], ns)
            if HAS_ALARM:
                signal.alarm(0)
            expected = eval(t["expected_expression"], {})
            r["actual"] = repr(actual)
            r["status"] = "PASS" if actual == expected else "FAIL"
        except Timeout:
            r["status"], r["error"] = "TIMEOUT", "Test exceeded 2 seconds (possible infinite loop)"
        except BaseException as e:
            r["error"] = "%s: %s" % (type(e).__name__, e)
            if HAS_ALARM:
                signal.alarm(0)
    results.append(r)
sys.stdout = real_stdout
finish()
'''


def _limits():  # POSIX only
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))


def run_python_tests(code: str, tests, timeout: int = 10):
    """tests: list of objects with name, call_expression, expected_expression. Returns list of result dicts."""
    if not tests:
        return []
    payload = [{"name": t.name, "call_expression": t.call_expression,
                "expected_expression": t.expected_expression} for t in tests]
    with tempfile.TemporaryDirectory() as tmp:
        for fname, content in (("code.py", code), ("tests.json", json.dumps(payload)), ("runner.py", RUNNER)):
            with open(os.path.join(tmp, fname), "w", encoding="utf-8") as f:
                f.write(content)
        env = {"PYTHONIOENCODING": "utf-8"}  # nothing else: API keys never reach submitted code
        if os.name == "nt":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
        kwargs = {"preexec_fn": _limits} if os.name == "posix" else {"creationflags": 0x08000000}
        try:
            subprocess.run([sys.executable, "-I", "runner.py"], cwd=tmp, env=env, timeout=timeout,
                           capture_output=True, text=True, **kwargs)
        except subprocess.TimeoutExpired:
            return [{"name": p["name"], "status": "TIMEOUT", "actual": "",
                     "error": f"Execution exceeded {timeout}s (possible infinite loop)"} for p in payload]
        path = os.path.join(tmp, "results.json")
        if not os.path.exists(path):
            return [{"name": p["name"], "status": "ERROR", "actual": "",
                     "error": "Sandbox process crashed before producing results"} for p in payload]
        with open(path, encoding="utf-8") as f:
            return json.load(f)
